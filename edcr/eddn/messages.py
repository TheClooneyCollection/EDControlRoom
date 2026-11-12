"""Parse EDDN relay envelopes into the market, station and system updates we store.

Only live-galaxy `commodity/3`, `journal/1` (Docked, CarrierJump, FSDJump, Location) and
`fsssignaldiscovered/1` (fleet carrier names) messages are used; test schemas and legacy-galaxy
uploads are dropped.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from edcr.recent_markets import MarketSnapshot as GameMarket, commodity_key

COMMODITY_SCHEMA = "https://eddn.edcd.io/schemas/commodity/3"
JOURNAL_SCHEMA = "https://eddn.edcd.io/schemas/journal/1"
SIGNAL_SCHEMA = "https://eddn.edcd.io/schemas/fsssignaldiscovered/1"

_POSITION_EVENTS = frozenset({"Docked", "CarrierJump", "FSDJump", "Location"})
_STATION_EVENTS = frozenset({"Docked", "CarrierJump"})
# Fleet carrier callsigns, e.g. `K7Q-BQL`. Market ids cannot tell carriers apart:
# colonisation stations also use ids above 3.7 billion.
_CARRIER_NAME = re.compile(r"^[A-Z0-9]{3}-[A-Z0-9]{3}$")
# A carrier signal reads "<display name> <callsign>"; the name is user-set and may be blank.
_CARRIER_SIGNAL = re.compile(r"^(.*?)\s*([A-Z0-9]{3}-[A-Z0-9]{3})$")


@dataclass(frozen=True)
class CommodityPrice:
    name: str
    buy: int
    sell: int
    supply: int
    demand: int


@dataclass(frozen=True)
class MarketSnapshot:
    market_id: int
    system_name: str
    station_name: str
    is_carrier: bool
    timestamp: float
    prices: tuple[CommodityPrice, ...]
    # A carrier's docking access (all, squadron, friends, squadronfriends, none); "" when the message omits it.
    carrier_access: str


@dataclass(frozen=True)
class SystemPosition:
    address: int
    name: str
    x: float
    y: float
    z: float
    timestamp: float


@dataclass(frozen=True)
class StationInfo:
    market_id: int
    system_address: int
    system_name: str
    name: str
    type: str
    dist_ls: float | None
    max_pad: str
    timestamp: float


@dataclass(frozen=True)
class StationTypeSeen:
    """A station type from our own Market.json, which names no system address or pads."""

    market_id: int
    system_name: str
    name: str
    type: str
    timestamp: float


@dataclass(frozen=True)
class CarrierName:
    """A fleet carrier's display name, keyed by callsign (its station name); the signal names no market id."""

    callsign: str
    name: str
    timestamp: float


EddnUpdate = MarketSnapshot | SystemPosition | StationInfo | StationTypeSeen | CarrierName


def is_carrier_station(name: str, station_type: str) -> bool:
    return station_type == "FleetCarrier" or bool(_CARRIER_NAME.match(name))


def parse_eddn_message(envelope: Any) -> list[EddnUpdate]:
    """Return the updates in one decoded relay envelope; [] when it is not used."""
    if not isinstance(envelope, dict):
        return []
    header = envelope.get("header")
    message = envelope.get("message")
    if not isinstance(header, dict) or not isinstance(message, dict) or _is_legacy(header):
        return []
    schema = envelope.get("$schemaRef")
    timestamp = _timestamp(message.get("timestamp"))
    if timestamp is None:
        return []
    if schema == COMMODITY_SCHEMA:
        snapshot = _market_snapshot(message, timestamp)
        return [snapshot] if snapshot is not None else []
    if schema == JOURNAL_SCHEMA:
        return _journal_updates(message, timestamp)
    if schema == SIGNAL_SCHEMA:
        return _carrier_names(message, timestamp)
    return []


def journal_event_updates(event: Any) -> list[EddnUpdate]:
    """The system and station facts in one of our own journal events, read as EDDN reads uploads of it."""
    if not isinstance(event, dict):
        return []
    timestamp = _timestamp(event.get("timestamp"))
    return _journal_updates(event, timestamp) if timestamp is not None else []


def station_type_from_game(game: GameMarket) -> StationTypeSeen | None:
    timestamp = _timestamp(game.timestamp)
    if timestamp is None or not game.station_type:
        return None
    return StationTypeSeen(market_id=game.market_id, system_name=game.system, name=game.station,
                           type=game.station_type, timestamp=timestamp)


def _is_legacy(header: dict[str, Any]) -> bool:
    version = str(header.get("gameversion") or "")
    return "Legacy" in version or version[:2] in {"2.", "3."}


def _timestamp(value: object) -> float | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.timestamp() if parsed.tzinfo is not None else None


def _market_snapshot(message: dict[str, Any], timestamp: float) -> MarketSnapshot | None:
    market_id = message.get("marketId")
    system_name = message.get("systemName")
    station_name = message.get("stationName")
    commodities = message.get("commodities")
    if not isinstance(market_id, int) or not isinstance(system_name, str) or not isinstance(station_name, str):
        return None
    if not isinstance(commodities, list):
        return None
    prices = tuple(price for price in (_price(item) for item in commodities) if price is not None)
    return MarketSnapshot(
        market_id=market_id,
        system_name=system_name,
        station_name=station_name,
        is_carrier=is_carrier_station(station_name, str(message.get("stationType") or "")),
        timestamp=timestamp,
        prices=prices,
        carrier_access=str(message.get("carrierDockingAccess") or "").strip().lower(),
    )


def market_snapshot_from_game(game: GameMarket) -> MarketSnapshot | None:
    """Our captured Market.json in the shape an EDDN commodity message parses to.

    It keeps the game's own timestamp, so it competes with EDDN data on the same newest-wins rule.
    """
    timestamp = _timestamp(game.timestamp)
    if timestamp is None or not game.station or not game.system:
        return None
    commodities = [
        {"name": commodity_key(str(item.get("Name") or "")), "buyPrice": item.get("BuyPrice"),
         "sellPrice": item.get("SellPrice"), "stock": item.get("Stock"), "demand": item.get("Demand")}
        for item in game.items
    ]
    return _market_snapshot({"marketId": game.market_id, "systemName": game.system, "stationName": game.station,
                             "stationType": game.station_type, "carrierDockingAccess": game.carrier_access,
                             "commodities": commodities}, timestamp)


def _carrier_names(message: dict[str, Any], timestamp: float) -> list[EddnUpdate]:
    signals = message.get("signals")
    if not isinstance(signals, list):
        return []
    names: list[EddnUpdate] = []
    for signal in signals:
        if not isinstance(signal, dict) or signal.get("SignalType") != "FleetCarrier":
            continue
        match = _CARRIER_SIGNAL.match(str(signal.get("SignalName") or "").strip())
        if match is not None and match.group(1).strip():
            names.append(CarrierName(callsign=match.group(2), name=match.group(1).strip(), timestamp=timestamp))
    return names


def _price(item: object) -> CommodityPrice | None:
    """A tradeable price row; rows the station neither sells nor wants are dropped."""
    if not isinstance(item, dict) or not isinstance(item.get("name"), str):
        return None
    values = [item.get(key) for key in ("buyPrice", "sellPrice", "stock", "demand")]
    if not all(isinstance(value, (int, float)) for value in values):
        return None
    buy, sell, supply, demand = (int(value) for value in values)
    if not (buy > 0 and supply > 0) and not (sell > 0 and demand > 0):
        return None
    return CommodityPrice(name=item["name"].lower(), buy=buy, sell=sell, supply=supply, demand=demand)


def _journal_updates(message: dict[str, Any], timestamp: float) -> list[EddnUpdate]:
    event = message.get("event")
    if event not in _POSITION_EVENTS:
        return []
    address = message.get("SystemAddress")
    system_name = message.get("StarSystem")
    position = message.get("StarPos")
    if not isinstance(address, int) or not isinstance(system_name, str):
        return []
    updates: list[EddnUpdate] = []
    if (
        isinstance(position, list)
        and len(position) == 3
        and all(isinstance(value, (int, float)) for value in position)
    ):
        x, y, z = (float(value) for value in position)
        updates.append(SystemPosition(address=address, name=system_name, x=x, y=y, z=z, timestamp=timestamp))
    docked = event in _STATION_EVENTS or (event == "Location" and message.get("Docked") is True)
    station = _station_info(message, address, system_name, timestamp) if docked else None
    if station is not None:
        updates.append(station)
    return updates


def _station_info(message: dict[str, Any], address: int, system_name: str, timestamp: float) -> StationInfo | None:
    market_id = message.get("MarketID")
    name = message.get("StationName")
    if not isinstance(market_id, int) or not isinstance(name, str):
        return None
    dist = message.get("DistFromStarLS")
    return StationInfo(
        market_id=market_id,
        system_address=address,
        system_name=system_name,
        name=name,
        type=str(message.get("StationType") or ""),
        dist_ls=float(dist) if isinstance(dist, (int, float)) else None,
        max_pad=_max_pad(message.get("LandingPads")),
        timestamp=timestamp,
    )


def _max_pad(pads: object) -> str:
    if not isinstance(pads, dict):
        return ""
    for size, key in (("L", "Large"), ("M", "Medium"), ("S", "Small")):
        count = pads.get(key)
        if isinstance(count, int) and count > 0:
            return size
    return ""
