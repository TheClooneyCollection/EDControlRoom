"""Parse EDDN relay envelopes into the market, station and system updates we store.

Only live-galaxy `commodity/3` and `journal/1` (Docked, CarrierJump, FSDJump,
Location) messages are used; test schemas and legacy-galaxy uploads are dropped.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

COMMODITY_SCHEMA = "https://eddn.edcd.io/schemas/commodity/3"
JOURNAL_SCHEMA = "https://eddn.edcd.io/schemas/journal/1"

_POSITION_EVENTS = frozenset({"Docked", "CarrierJump", "FSDJump", "Location"})
_STATION_EVENTS = frozenset({"Docked", "CarrierJump"})
# Fleet carrier callsigns, e.g. `K7Q-BQL`. Market ids cannot tell carriers apart:
# colonisation stations also use ids above 3.7 billion.
_CARRIER_NAME = re.compile(r"^[A-Z0-9]{3}-[A-Z0-9]{3}$")


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


EddnUpdate = MarketSnapshot | SystemPosition | StationInfo


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
    return []


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
    )


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
    station = _station_info(message, address, system_name, timestamp) if event in _STATION_EVENTS else None
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
