"""Recently visited station markets, captured from Elite's Market.json.

Only market snapshots live here; station and system facts go to the market store (`edcr.eddn.store`).
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import tempfile
import threading
from typing import Any, Callable

_SCHEMA = 1
# One recent-markets file is read, changed and saved under this, so the hub's own captures and its peers'
# pushed markets never drop each other's stations.
_RECORD_LOCK = threading.Lock()


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
    limit: int,
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
    payload = {
        "schema": _SCHEMA,
        "markets": [snapshot_entry(snapshot) for snapshot in snapshots],
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


def record_market_json(path: Path, data: dict[str, Any], log: Callable[[str], None], *, limit: int) -> bool:
    """Store a Market.json payload; True when the store changed."""
    snapshot = snapshot_from_market_json(data)
    return snapshot is not None and record_market(path, snapshot, log, limit=limit)


def record_market(path: Path, snapshot: MarketSnapshot, log: Callable[[str], None], *, limit: int) -> bool:
    """Store one market snapshot (this game's, or on a hub one a peer pushed); True when the store changed."""
    with _RECORD_LOCK:
        current = load_recent_markets(path)
        updated = record_snapshot(current, snapshot, limit=limit)
        if updated == current:
            return False
        try:
            save_recent_markets(path, updated)
        except OSError as exc:
            log(f"Warning: failed to save recent markets to {path}: {exc}")
            return False
    return True


def _int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    return 0


def watch_file(
    path: Path,
    interval_s: float,
    on_change: Callable[[Path], None],
    *,
    stop: threading.Event,
    log: Callable[[str], None],
    name: str,
) -> threading.Thread:
    """Call `on_change` at start and whenever the file's mtime changes, until `stop` is set."""

    def watch() -> None:
        last_mtime: float | None = None
        while True:
            try:
                mtime: float | None = path.stat().st_mtime
            except OSError:
                mtime = None
            if mtime is not None and mtime != last_mtime:
                last_mtime = mtime
                try:
                    on_change(path)
                except Exception as exc:  # A bad push or import must not end the watcher.
                    log(f"Watcher {name} error: {exc}")
            if stop.wait(interval_s):
                return

    thread = threading.Thread(target=watch, name=name, daemon=True)
    thread.start()
    return thread
