from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

from edap.cargo_manifest import read_cargo_inventory
from edap.config import AppConfig
from edap.control_room import rendering as _rendering
from edap.control_room.models import MarketData, ShipState
from edap.recent_markets import JOURNAL_PLACE_EVENTS, record_journal_events, record_market_json
from edap.status import read_status
from edap.state import get_latest_journal_log, read_ship_state


class BootstrapHost(Protocol):
    _journal_dir: Path
    _market_path: Path
    _market_mtime: float | None
    _market: MarketData
    _ship: ShipState
    _config: AppConfig

    def _refresh_market(self) -> None: ...
    def _log(self, msg: str) -> None: ...


def sync_cargo_manifest(app: BootstrapHost, *, update_count: bool = True) -> bool:
    cargo_path = app._journal_dir / "Cargo.json"
    if not cargo_path.exists():
        return False
    inventory = read_cargo_inventory(app._journal_dir)
    app._ship.cargo_inventory = list(inventory)
    if update_count:
        app._ship.cargo_count = sum(int(item.get("Count", 0) or 0) for item in inventory)
    return True


def sync_status_state(app: BootstrapHost) -> None:
    try:
        status = read_status(app._journal_dir)
    except Exception:
        status = None

    if status is None:
        return

    if status.balance is not None:
        app._ship.credits = status.balance
    if status.cargo is not None:
        app._ship.cargo_count = int(status.cargo)
    app._ship.destination_system = status.destination_system
    app._ship.destination_body = status.destination_body
    app._ship.destination_name = status.destination_name


def bootstrap_ship_state(app: BootstrapHost) -> None:
    log = get_latest_journal_log(app._journal_dir)
    if log is not None:
        try:
            state = read_ship_state(log)
            app._ship.commander = state.commander
            app._ship.system = state.location
            app._ship.station = state.station
            app._ship.status = state.status
            app._ship.ship_type = state.ship_type
            app._ship.fuel_level = state.fuel_level
            app._ship.fuel_capacity = state.fuel_capacity
            app._ship.target = state.target
            app._ship.cargo_capacity = state.cargo_capacity
            app._ship.max_jump_range_ly = state.max_jump_range_ly
        except Exception:
            pass
        record_journal_places(app, log)

    sync_status_state(app)
    if not sync_cargo_manifest(app, update_count=False):
        app._ship.cargo_inventory = _rendering.read_cargo_inventory(app._journal_dir)


def record_journal_places(app: BootstrapHost, log_path: Path) -> None:
    """Keep the station and system places of the latest journal, which predate this launch."""
    events = []
    try:
        with log_path.open(encoding="utf-8") as handle:
            for line in handle:
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if isinstance(event, dict) and event.get("event") in JOURNAL_PLACE_EVENTS:
                    events.append(event)
    except OSError:
        return
    record_journal_events(app._config.control_room.recent_markets_file, events, app._log)


def load_market_json(app: BootstrapHost) -> None:
    if not app._market_path.exists():
        return
    mtime = app._market_path.stat().st_mtime
    if mtime == app._market_mtime:
        return
    app._market_mtime = mtime
    try:
        with app._market_path.open(encoding="utf-8") as fh:
            data: dict[str, Any] = json.load(fh)
    except Exception:
        return
    record_market_json(app._config.control_room.recent_markets_file, data, app._log)

    station = data.get("StationName", "?")
    system = data.get("StarSystem", "?")
    if app._ship.status == "in_station":
        if app._ship.station:
            station = app._ship.station
        if app._ship.system:
            system = app._ship.system

    app._market = MarketData(
        station=station,
        system=system,
        timestamp=data.get("timestamp", ""),
        market_id=_int_or_none(data.get("MarketID")),
        items=data.get("Items", []),
        locked=app._market.locked,
    )
    if app._ship.status == "in_station":
        market_station = app._market.station
        if not app._ship.station and market_station and market_station != "?":
            app._ship.station = market_station
        market_system = app._market.system
        if not app._ship.system and market_system and market_system != "?":
            app._ship.system = market_system
    app._refresh_market()


def _int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
