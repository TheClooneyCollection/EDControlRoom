from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


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
    session_completed_runs: int = 0
    session_total_run_elapsed_seconds: float = 0.0
    session_last_run_profit: int | None = None
    session_last_run_elapsed_seconds: float | None = None


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
    session_completed_runs = raw.get("session_completed_runs", 0)
    if not isinstance(session_completed_runs, int):
        session_completed_runs = 0
    session_total_run_elapsed_seconds = raw.get("session_total_run_elapsed_seconds", 0.0)
    if not isinstance(session_total_run_elapsed_seconds, (int, float)):
        session_total_run_elapsed_seconds = 0.0
    session_last_run_profit = raw.get("session_last_run_profit")
    if not isinstance(session_last_run_profit, int):
        session_last_run_profit = None
    session_last_run_elapsed_seconds = raw.get("session_last_run_elapsed_seconds")
    if not isinstance(session_last_run_elapsed_seconds, (int, float)):
        session_last_run_elapsed_seconds = None

    return ControlRoomState(
        default_haul={str(key): str(value) for key, value in default_haul.items()},
        history=history,
        instant_mode=instant_mode,
        session_profit=session_profit,
        session_elapsed_seconds=float(session_elapsed_seconds),
        session_completed_runs=session_completed_runs,
        session_total_run_elapsed_seconds=float(session_total_run_elapsed_seconds),
        session_last_run_profit=session_last_run_profit,
        session_last_run_elapsed_seconds=(
            float(session_last_run_elapsed_seconds)
            if session_last_run_elapsed_seconds is not None
            else None
        ),
    )


def save_control_room_state(path: Path, state: ControlRoomState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "default_haul": state.default_haul,
        "instant_mode": state.instant_mode,
        "session_profit": state.session_profit,
        "session_elapsed_seconds": state.session_elapsed_seconds,
        "session_completed_runs": state.session_completed_runs,
        "session_total_run_elapsed_seconds": state.session_total_run_elapsed_seconds,
        "session_last_run_profit": state.session_last_run_profit,
        "session_last_run_elapsed_seconds": state.session_last_run_elapsed_seconds,
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
