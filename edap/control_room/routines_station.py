"""Station routine launchers (dock, undock)."""
from __future__ import annotations

from edap.control_room.interfaces import RoutineHost
from edap.routines import dock, undock


def _should_wait_for_supercruise_exit(status: str | None) -> bool:
    return status in {"in_supercruise", "supercruise"}


def cmd_dock(app: RoutineHost, *, skip_delay: bool = False) -> None:
    if not app._check_routine_ready():
        return
    wait_for_scx = _should_wait_for_supercruise_exit(app._ship.status)
    progress = app._make_progress()
    controls = app._make_controls(progress)
    sleeper = app._make_sleeper()
    time_fn = app._time_fn
    step_delay = app._config.controls.step_delay_seconds
    supercruise_exit_settle = app._config.controls.dock_supercruise_exit_settle_seconds
    watcher = app._make_watcher()

    label = "dock (waiting for supercruise exit)" if wait_for_scx else "dock (already in space)"
    app._start_delayed_routine(
        description=label,
        start_message=f"Starting {label}, auto-refuel/repair on...",
        skip_delay=skip_delay,
        fn=lambda: dock(
            controls,
            watcher,
            wait_for_supercruise_exit=wait_for_scx,
            auto_refuel=True,
            step_delay_s=step_delay,
            supercruise_exit_settle_s=supercruise_exit_settle,
            time_fn=time_fn,
            sleeper=sleeper,
            progress_fn=progress,
            announce_fn=app._announce_tts,
            announce_station_name=app._ship.station or "",
        ),
    )


def cmd_undock(app: RoutineHost, *, skip_delay: bool = False) -> None:
    if not app._check_routine_ready():
        return
    progress = app._make_progress()
    controls = app._make_controls(progress)
    sleeper = app._make_sleeper()
    time_fn = app._time_fn
    step_delay = app._config.controls.step_delay_seconds
    undock_timeout = app._config.controls.undock_timeout_seconds
    no_track_timeout = app._config.controls.undock_no_track_timeout_seconds
    watcher = app._make_watcher()

    app._start_delayed_routine(
        description="undock",
        start_message="Starting undock...",
        skip_delay=skip_delay,
        fn=lambda: undock(
            controls,
            watcher,
            undock_timeout_s=undock_timeout,
            no_track_timeout_s=no_track_timeout,
            step_delay_s=step_delay,
            time_fn=time_fn,
            sleeper=sleeper,
            progress_fn=progress,
        ),
    )
