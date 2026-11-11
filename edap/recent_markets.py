"""Recently visited station markets, captured from Elite's Market.json.

The same store keeps journal places: each docked station's distance from the star and type
(`Docked`) and each visited system's coordinates (`FSDJump`, `Location`, `CarrierJump`), so
a Best deal trip time can be estimated without EDDN.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Callable

RECENT_MARKETS_LIMIT = 10
JOURNAL_PLACES_LIMIT = 50
_SCHEMA = 1
_POSITION_EVENTS = frozenset({"FSDJump", "Location", "CarrierJump"})
JOURNAL_PLACE_EVENTS = _POSITION_EVENTS | {"Docked"}


@dataclass(frozen=True)
class MarketSnapshot:
    market_id: int
    station: str
    system: str
    station_type: str
    timestamp: str
    items: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class MarketItem:
    commodity: str
    name: str
    category: str
    buy_price: int
    sell_price: int
    mean_price: int
    stock: int
    demand: int
    stock_bracket: int
    demand_bracket: int


@dataclass(frozen=True)
class StationPlace:
    market_id: int
    station: str
    system: str
    station_type: str
    dist_ls: float | None
    timestamp: str


@dataclass(frozen=True)
class SystemPlace:
    system: str
    x: float
    y: float
    z: float
    timestamp: str


@dataclass(frozen=True)
class JournalPlaces:
    """Newest first, one entry per station and per system."""

    stations: tuple[StationPlace, ...] = ()
    systems: tuple[SystemPlace, ...] = ()

    def station(self, market_id: int) -> StationPlace | None:
        return next((place for place in self.stations if place.market_id == market_id), None)

    def system(self, name: str) -> SystemPlace | None:
        key = name.casefold()
        return next((place for place in self.systems if place.system.casefold() == key), None)


def commodity_key(name: str) -> str:
    """Normalise `$hazardousenvironmentsuits_name;` to `hazardousenvironmentsuits`."""
    key = name.strip().lower()
    if key.startswith("$"):
        key = key[1:]
    if key.endswith(";"):
        key = key[:-1]
    if key.endswith("_name"):
        key = key[: -len("_name")]
    return key


def snapshot_from_market_json(data: dict[str, Any]) -> MarketSnapshot | None:
    market_id = data.get("MarketID")
    items = data.get("Items")
    if isinstance(market_id, bool) or not isinstance(market_id, int) or not isinstance(items, list):
        return None
    return MarketSnapshot(
        market_id=market_id,
        station=str(data.get("StationName") or ""),
        system=str(data.get("StarSystem") or ""),
        station_type=str(data.get("StationType") or ""),
        timestamp=str(data.get("timestamp") or ""),
        items=tuple(item for item in items if isinstance(item, dict)),
    )


def record_snapshot(
    snapshots: tuple[MarketSnapshot, ...],
    snapshot: MarketSnapshot,
    *,
    limit: int = RECENT_MARKETS_LIMIT,
) -> tuple[MarketSnapshot, ...]:
    """Return snapshots newest first, one per station; a stale snapshot changes nothing."""
    existing = next((s for s in snapshots if s.market_id == snapshot.market_id), None)
    if existing is not None and existing.timestamp >= snapshot.timestamp:
        return snapshots
    others = [s for s in snapshots if s.market_id != snapshot.market_id]
    ordered = sorted([snapshot, *others], key=lambda s: s.timestamp, reverse=True)
    return tuple(ordered[:limit])


def market_items(snapshot: MarketSnapshot) -> tuple[MarketItem, ...]:
    rows = []
    for item in snapshot.items:
        raw_name = str(item.get("Name") or "")
        key = commodity_key(raw_name)
        if not key:
            continue
        rows.append(
            MarketItem(
                commodity=key,
                name=str(item.get("Name_Localised") or key),
                category=str(item.get("Category_Localised") or ""),
                buy_price=_int(item.get("BuyPrice")),
                sell_price=_int(item.get("SellPrice")),
                mean_price=_int(item.get("MeanPrice")),
                stock=_int(item.get("Stock")),
                demand=_int(item.get("Demand")),
                stock_bracket=_int(item.get("StockBracket")),
                demand_bracket=_int(item.get("DemandBracket")),
            )
        )
    return tuple(rows)


def _read_payload(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def load_recent_markets(path: Path) -> tuple[MarketSnapshot, ...]:
    """Read the store; a missing or unreadable file is an empty history."""
    return _snapshots_from_payload(_read_payload(path))


def _snapshots_from_payload(payload: dict[str, Any]) -> tuple[MarketSnapshot, ...]:
    markets = payload.get("markets")
    if not isinstance(markets, list):
        return ()
    snapshots = [snapshot_from_entry(entry) for entry in markets]
    return tuple(snapshot for snapshot in snapshots if snapshot is not None)


def load_journal_places(path: Path) -> JournalPlaces:
    """Read the journal places; a missing or unreadable store has none."""
    return _places_from_payload(_read_payload(path))


def _places_from_payload(payload: dict[str, Any]) -> JournalPlaces:
    places = payload.get("places")
    if not isinstance(places, dict):
        return JournalPlaces()
    stations = []
    for entry in places.get("stations") or []:
        if not isinstance(entry, dict) or not _is_int(entry.get("market_id")):
            continue
        dist = entry.get("dist_ls")
        stations.append(StationPlace(
            market_id=entry["market_id"], station=str(entry.get("station") or ""),
            system=str(entry.get("system") or ""), station_type=str(entry.get("station_type") or ""),
            dist_ls=float(dist) if _is_number(dist) else None, timestamp=str(entry.get("timestamp") or ""),
        ))
    systems = []
    for entry in places.get("systems") or []:
        if not isinstance(entry, dict) or not all(_is_number(entry.get(axis)) for axis in "xyz"):
            continue
        systems.append(SystemPlace(
            system=str(entry.get("system") or ""), x=float(entry["x"]), y=float(entry["y"]), z=float(entry["z"]),
            timestamp=str(entry.get("timestamp") or ""),
        ))
    return JournalPlaces(stations=tuple(stations), systems=tuple(systems))


def record_places(places: JournalPlaces, event: dict[str, Any], *, limit: int = JOURNAL_PLACES_LIMIT) -> JournalPlaces:
    """Fold one journal event into the places; events that carry none change nothing."""
    name = event.get("event")
    timestamp = str(event.get("timestamp") or "")
    system = event.get("StarSystem")
    stations, systems = places.stations, places.systems
    position = event.get("StarPos")
    if (
        name in _POSITION_EVENTS and isinstance(system, str) and system
        and isinstance(position, list) and len(position) == 3 and all(_is_number(value) for value in position)
    ):
        x, y, z = (float(value) for value in position)
        place = SystemPlace(system=system, x=x, y=y, z=z, timestamp=timestamp)
        key = system.casefold()
        systems = (place, *(entry for entry in systems if entry.system.casefold() != key))[:limit]
    docked = name == "Docked" or (name in {"Location", "CarrierJump"} and event.get("Docked") is True)
    market_id = event.get("MarketID")
    if docked and _is_int(market_id):
        dist = event.get("DistFromStarLS")
        place = StationPlace(
            market_id=market_id, station=str(event.get("StationName") or ""), system=str(system or ""),
            station_type=str(event.get("StationType") or ""),
            dist_ls=float(dist) if _is_number(dist) else None, timestamp=timestamp,
        )
        stations = (place, *(entry for entry in stations if entry.market_id != market_id))[:limit]
    return JournalPlaces(stations=stations, systems=systems)


def record_journal_events(path: Path, events: list[dict[str, Any]], log: Callable[[str], None]) -> bool:
    """Store the places in these journal events; True when the store changed."""
    payload = _read_payload(path)
    current = _places_from_payload(payload)
    updated = current
    for event in events:
        updated = record_places(updated, event)
    if updated == current:
        return False
    try:
        _save_payload(path, _snapshots_from_payload(payload), updated)
    except OSError as exc:
        log(f"Warning: failed to save journal places to {path}: {exc}")
        return False
    return True


def snapshot_from_entry(entry: object) -> MarketSnapshot | None:
    """One stored entry (the shape `snapshot_entry` writes); None when it is not one."""
    if not isinstance(entry, dict):
        return None
    return snapshot_from_market_json(
        {
            "MarketID": entry.get("market_id"),
            "StationName": entry.get("station"),
            "StarSystem": entry.get("system"),
            "StationType": entry.get("station_type"),
            "timestamp": entry.get("timestamp"),
            "Items": entry.get("items"),
        }
    )


def snapshot_entry(snapshot: MarketSnapshot) -> dict[str, Any]:
    return {
        "market_id": snapshot.market_id,
        "station": snapshot.station,
        "system": snapshot.system,
        "station_type": snapshot.station_type,
        "timestamp": snapshot.timestamp,
        "items": list(snapshot.items),
    }


def save_recent_markets(path: Path, snapshots: tuple[MarketSnapshot, ...]) -> None:
    """Replace the markets; the journal places already stored are kept."""
    _save_payload(path, snapshots, load_journal_places(path))


def _save_payload(path: Path, snapshots: tuple[MarketSnapshot, ...], places: JournalPlaces) -> None:
    payload = {
        "schema": _SCHEMA,
        "markets": [snapshot_entry(snapshot) for snapshot in snapshots],
        "places": {
            "stations": [asdict(place) for place in places.stations],
            "systems": [asdict(place) for place in places.systems],
        },
    }
    directory = path.parent if str(path.parent) else Path(".")
    directory.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise


def record_market_json(path: Path, data: dict[str, Any], log: Callable[[str], None]) -> bool:
    """Store a Market.json payload; True when the store changed."""
    snapshot = snapshot_from_market_json(data)
    if snapshot is None:
        return False
    current = load_recent_markets(path)
    updated = record_snapshot(current, snapshot)
    if updated == current:
        return False
    try:
        save_recent_markets(path, updated)
    except OSError as exc:
        log(f"Warning: failed to save recent markets to {path}: {exc}")
        return False
    return True


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value == value


def _int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    return 0
