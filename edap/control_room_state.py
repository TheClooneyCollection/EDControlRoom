from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from edap.inara.trade_routes import TradeRoute


@dataclass
class CommandHistoryEntry:
    raw: str
    command: str
    params: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""


@dataclass
class ControlRoomState:
    default_haul: dict[str, str] = field(default_factory=dict)
    history: list[CommandHistoryEntry] = field(default_factory=list)
    instant_mode: bool = False
    session_profit: int = 0
    session_elapsed_seconds: float = 0.0
    session_active: bool = False
    session_completed_runs: int = 0
    session_total_run_elapsed_seconds: float = 0.0
    session_last_run_profit: int | None = None
    session_last_run_profit_delta: int | None = None
    session_last_run_elapsed_seconds: float | None = None
    session_expected_profit_per_trip: int | None = None
    session_expected_profit_per_trip_text: str = ""
    selected_trade_route: TradeRoute | None = None
    running_trade_route: TradeRoute | None = None


_LEGACY_HAUL_KEYS = frozenset({"commodity", "buy_station", "sell_station", "buy_system", "sell_system"})
_TWO_WAY_HAUL_KEYS = frozenset({"station_1_buying", "station_2_buying", "station_1", "station_2"})


def _is_legacy_haul_params(params: dict[str, Any]) -> bool:
    keys = set(params.keys())
    return bool(keys & _LEGACY_HAUL_KEYS) and not (keys & _TWO_WAY_HAUL_KEYS)


def _is_search_haul_params(params: dict[str, Any]) -> bool:
    return str(params.get("mode", "")).strip().lower() == "search"


def load_control_room_state(path: Path) -> ControlRoomState:
    if not path.exists():
        return ControlRoomState()

    with path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    if not isinstance(raw, dict):
        return ControlRoomState()

    default_haul = raw.get("default_haul", raw.get("haul_defaults", {}))
    if not isinstance(default_haul, dict):
        default_haul = {}
    elif _is_legacy_haul_params(default_haul):
        default_haul = {}
    elif _is_search_haul_params(default_haul):
        default_haul = {}

    raw_history = raw.get("history", [])
    history: list[CommandHistoryEntry] = []
    if isinstance(raw_history, list):
        for item in raw_history:
            if not isinstance(item, dict):
                continue
            raw_command = item.get("raw", "")
            command = item.get("command", "")
            params = item.get("params", {})
            timestamp = item.get("timestamp", "")
            if not isinstance(raw_command, str) or not isinstance(command, str):
                continue
            if not isinstance(params, dict):
                params = {}
            if not isinstance(timestamp, str):
                timestamp = ""
            if command == "haul" and _is_legacy_haul_params(params):
                continue
            history.append(
                CommandHistoryEntry(
                    raw=raw_command,
                    command=command,
                    params=params,
                    timestamp=timestamp,
                )
            )

    instant_mode = raw.get("instant_mode", False)
    if not isinstance(instant_mode, bool):
        instant_mode = False

    session_profit = raw.get("session_profit", 0)
    if not isinstance(session_profit, int):
        session_profit = 0
    session_elapsed_seconds = raw.get("session_elapsed_seconds", 0.0)
    if not isinstance(session_elapsed_seconds, (int, float)):
        session_elapsed_seconds = 0.0
    session_active = raw.get("session_active", False)
    if not isinstance(session_active, bool):
        session_active = False
    session_completed_runs = raw.get("session_completed_runs", 0)
    if not isinstance(session_completed_runs, int):
        session_completed_runs = 0
    session_total_run_elapsed_seconds = raw.get("session_total_run_elapsed_seconds", 0.0)
    if not isinstance(session_total_run_elapsed_seconds, (int, float)):
        session_total_run_elapsed_seconds = 0.0
    session_last_run_profit = raw.get("session_last_run_profit")
    if not isinstance(session_last_run_profit, int):
        session_last_run_profit = None
    session_last_run_profit_delta = raw.get("session_last_run_profit_delta")
    if not isinstance(session_last_run_profit_delta, int):
        session_last_run_profit_delta = None
    session_last_run_elapsed_seconds = raw.get("session_last_run_elapsed_seconds")
    if not isinstance(session_last_run_elapsed_seconds, (int, float)):
        session_last_run_elapsed_seconds = None
    session_expected_profit_per_trip = raw.get("session_expected_profit_per_trip")
    if not isinstance(session_expected_profit_per_trip, int):
        session_expected_profit_per_trip = None
    session_expected_profit_per_trip_text = raw.get("session_expected_profit_per_trip_text", "")
    if not isinstance(session_expected_profit_per_trip_text, str):
        session_expected_profit_per_trip_text = ""
    selected_trade_route = _trade_route_from_payload(raw.get("selected_trade_route"))
    running_trade_route = _trade_route_from_payload(raw.get("running_trade_route"))

    return ControlRoomState(
        default_haul={str(key): str(value) for key, value in default_haul.items()},
        history=history,
        instant_mode=instant_mode,
        session_profit=session_profit,
        session_elapsed_seconds=float(session_elapsed_seconds),
        session_active=session_active,
        session_completed_runs=session_completed_runs,
        session_total_run_elapsed_seconds=float(session_total_run_elapsed_seconds),
        session_last_run_profit=session_last_run_profit,
        session_last_run_profit_delta=session_last_run_profit_delta,
        session_last_run_elapsed_seconds=(
            float(session_last_run_elapsed_seconds)
            if session_last_run_elapsed_seconds is not None
            else None
        ),
        session_expected_profit_per_trip=session_expected_profit_per_trip,
        session_expected_profit_per_trip_text=session_expected_profit_per_trip_text,
        selected_trade_route=selected_trade_route,
        running_trade_route=running_trade_route,
    )


def save_control_room_state(path: Path, state: ControlRoomState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "default_haul": state.default_haul,
        "instant_mode": state.instant_mode,
        "session_profit": state.session_profit,
        "session_elapsed_seconds": state.session_elapsed_seconds,
        "session_active": state.session_active,
        "session_completed_runs": state.session_completed_runs,
        "session_total_run_elapsed_seconds": state.session_total_run_elapsed_seconds,
        "session_last_run_profit": state.session_last_run_profit,
        "session_last_run_profit_delta": state.session_last_run_profit_delta,
        "session_last_run_elapsed_seconds": state.session_last_run_elapsed_seconds,
        "session_expected_profit_per_trip": state.session_expected_profit_per_trip,
        "session_expected_profit_per_trip_text": state.session_expected_profit_per_trip_text,
        "selected_trade_route": _trade_route_to_payload(state.selected_trade_route),
        "running_trade_route": _trade_route_to_payload(state.running_trade_route),
        "history": [
            {
                "raw": entry.raw,
                "command": entry.command,
                "params": entry.params,
                "timestamp": entry.timestamp,
            }
            for entry in state.history
        ],
    }

    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temp_path = Path(handle.name)

    temp_path.replace(path)


def _trade_route_from_payload(payload: object) -> TradeRoute | None:
    from edap.inara.trade_routes import TradeRoute

    if not isinstance(payload, dict):
        return None
    try:
        index = int(payload.get("index", 0))
    except (TypeError, ValueError):
        return None
    from_station = payload.get("from_station")
    from_system = payload.get("from_system")
    to_station = payload.get("to_station")
    to_system = payload.get("to_system")
    if not all(
        isinstance(value, str) and value.strip()
        for value in (from_station, from_system, to_station, to_system)
    ):
        return None
    url_links_value = payload.get("url_links", ())
    url_links = (
        tuple(str(value) for value in url_links_value)
        if isinstance(url_links_value, (list, tuple))
        else ()
    )
    return TradeRoute(
        index=index,
        from_station=from_station,
        from_system=from_system,
        to_station=to_station,
        to_system=to_system,
        source_buy_commodity=_optional_str(payload.get("source_buy_commodity")),
        target_buy_commodity=_optional_str(payload.get("target_buy_commodity")),
        from_station_distance=_optional_str(payload.get("from_station_distance")),
        to_station_distance=_optional_str(payload.get("to_station_distance")),
        distance_from_system=_optional_str(payload.get("distance_from_system")),
        route_distance=_optional_str(payload.get("route_distance")),
        profit_per_unit=_optional_str(payload.get("profit_per_unit")),
        profit_per_trip=_optional_str(payload.get("profit_per_trip")),
        profit_per_hour=_optional_str(payload.get("profit_per_hour")),
        from_supply=_optional_str(payload.get("from_supply")),
        from_demand=_optional_str(payload.get("from_demand")),
        to_supply=_optional_str(payload.get("to_supply")),
        to_demand=_optional_str(payload.get("to_demand")),
        updated=_optional_str(payload.get("updated")),
        raw_text=str(payload.get("raw_text", "")),
        url_links=url_links,
    )


def _trade_route_to_payload(route: TradeRoute | None) -> dict[str, Any] | None:
    return asdict(route) if route is not None else None


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    return value or None
