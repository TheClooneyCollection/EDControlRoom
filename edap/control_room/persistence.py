from __future__ import annotations

from pathlib import Path
from typing import Protocol

from rich.markup import escape

from edap.config import AppConfig
from edap.control_room.models import HaulStats
from edap.control_room_state import (
    CommandHistoryEntry,
    ControlRoomState,
    load_control_room_state,
    save_control_room_state,
)


class PersistenceHost(Protocol):
    _config: AppConfig
    _haul_stats: HaulStats
    _instant_mode: bool
    _saved_state: ControlRoomState
    _state_path: Path
    _history: list[str]
    _history_pos: int
    _history_draft: str
    _time_fn: object

    def _log(self, msg: str) -> None: ...


def load_saved_state(app: PersistenceHost) -> None:
    try:
        app._saved_state = load_control_room_state(app._state_path)
    except Exception as exc:
        app._saved_state = ControlRoomState()
        app._log(
            f"[yellow]Failed to load control-room state "
            f"from {escape(str(app._state_path))}: {escape(str(exc))}[/]"
        )
    app._history = [entry.raw for entry in app._saved_state.history if entry.raw]
    app._history_pos = len(app._history)
    app._instant_mode = app._saved_state.instant_mode
    _restore_persisted_session(app)
    if app._config.control_room.clear_session_on_launch:
        clear_session_stats(app)
        app._log("[dim]Cleared persisted haul session on launch.[/]")


def save_saved_state(app: PersistenceHost) -> None:
    app._saved_state.instant_mode = app._instant_mode
    _capture_persisted_session(app)
    try:
        save_control_room_state(app._state_path, app._saved_state)
    except Exception as exc:
        app._log(
            f"[yellow]Failed to save control-room state "
            f"to {escape(str(app._state_path))}: {escape(str(exc))}[/]"
        )


def record_history_entry(app: PersistenceHost, entry: CommandHistoryEntry) -> None:
    if (
        app._saved_state.history
        and app._saved_state.history[-1].raw == entry.raw
        and app._saved_state.history[-1].params == entry.params
    ):
        app._saved_state.history[-1] = entry
    else:
        app._saved_state.history.append(entry)

    limit = app._config.control_room.history_limit
    if len(app._saved_state.history) > limit:
        app._saved_state.history = app._saved_state.history[-limit:]

    app._history = [item.raw for item in app._saved_state.history if item.raw]
    app._history_pos = len(app._history)
    app._history_draft = ""
    save_saved_state(app)


def clear_session_stats(app: PersistenceHost) -> None:
    stats = app._haul_stats
    now_fn = app._time_fn
    now = now_fn() if callable(now_fn) else 0.0
    stats.session_started_at = now
    stats.session_elapsed_s = 0.0
    stats.session_active = True
    stats.accumulated_profit = 0
    stats.cargo_moved_t = 0
    stats.completed_runs = 0
    stats.total_run_elapsed_s = 0.0
    stats.last_run_profit = None
    stats.last_run_profit_delta = None
    stats.last_run_elapsed_s = None
    stats.current_run_profit = 0
    if stats.active:
        stats.current_run_started_at = now
        stats.current_run_elapsed_s = None
        stats.docked_back_at_station_1 = False
    else:
        stats.current_run_started_at = None
        stats.current_run_elapsed_s = None
    save_saved_state(app)


def stop_session_stats(app: PersistenceHost) -> None:
    stats = app._haul_stats
    if stats.active:
        raise ValueError("Stop the active haul before stopping the persisted session.")
    now_fn = app._time_fn
    now = now_fn() if callable(now_fn) else 0.0
    if stats.session_started_at is not None:
        stats.session_elapsed_s = max(0.0, now - stats.session_started_at)
    stats.session_started_at = None
    stats.session_active = False
    save_saved_state(app)


def _restore_persisted_session(app: PersistenceHost) -> None:
    saved = app._saved_state
    stats = app._haul_stats
    now_fn = app._time_fn
    now = now_fn() if callable(now_fn) else 0.0
    stats.session_elapsed_s = saved.session_elapsed_seconds
    stats.session_active = saved.session_active
    if saved.session_active:
        stats.session_started_at = max(0.0, now - saved.session_elapsed_seconds)
    else:
        stats.session_started_at = None
    stats.accumulated_profit = saved.session_profit
    stats.completed_runs = saved.session_completed_runs
    stats.total_run_elapsed_s = saved.session_total_run_elapsed_seconds
    stats.last_run_profit = saved.session_last_run_profit
    stats.last_run_profit_delta = saved.session_last_run_profit_delta
    stats.last_run_elapsed_s = saved.session_last_run_elapsed_seconds
    stats.expected_profit_per_trip = saved.session_expected_profit_per_trip
    stats.expected_profit_per_trip_text = saved.session_expected_profit_per_trip_text


def _capture_persisted_session(app: PersistenceHost) -> None:
    saved = app._saved_state
    stats = app._haul_stats
    now_fn = app._time_fn
    now = now_fn() if callable(now_fn) else 0.0
    session_elapsed = stats.session_elapsed_s
    if stats.session_started_at is not None:
        session_elapsed = max(0.0, now - stats.session_started_at)
    saved.session_profit = stats.accumulated_profit + stats.current_run_profit
    saved.session_elapsed_seconds = session_elapsed
    saved.session_active = stats.session_active
    saved.session_completed_runs = stats.completed_runs
    saved.session_total_run_elapsed_seconds = stats.total_run_elapsed_s
    saved.session_last_run_profit = stats.last_run_profit
    saved.session_last_run_profit_delta = stats.last_run_profit_delta
    saved.session_last_run_elapsed_seconds = stats.last_run_elapsed_s
    saved.session_expected_profit_per_trip = stats.expected_profit_per_trip
    saved.session_expected_profit_per_trip_text = stats.expected_profit_per_trip_text
