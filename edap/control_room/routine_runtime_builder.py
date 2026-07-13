"""Build a `RoutineRuntime` from control-room app state.

Kept out of the haul module so travel/spansh route can construct one without
pulling in market-only helpers.
"""
from __future__ import annotations

from typing import Callable

from edap.control_room.interfaces import HaulHost
from edap.routines._base import SupportsPollEvents, SupportsRoutineControls
from edap.routines.callbacks import AnnouncementCallback, ProgressCallback
from edap.routines.runtime import RoutineRuntime, RoutineTiming, RoutineTravelSettings


def build_routine_runtime(
    app: HaulHost,
    *,
    controls: SupportsRoutineControls,
    watcher: SupportsPollEvents,
    sleeper: Callable[[float], None],
    time_fn: Callable[[], float],
    progress_fn: ProgressCallback,
    dock_timeout_s: float,
    galaxy_map_settle_s: float,
    request_timeout_s: float = 20.0,
    settle_s: float = 2.0,
    boost_settle_s: float = 3.0,
    deny_retry_delay_s: float = 5.0,
    announce_fn: AnnouncementCallback | None = None,
) -> RoutineRuntime:
    cfg = app._config.controls
    return RoutineRuntime(
        controls=controls,
        watcher=watcher,
        journal_dir=app._journal_dir,
        timing=RoutineTiming(
            step_delay_s=cfg.step_delay_seconds,
            dock_timeout_s=dock_timeout_s,
            request_timeout_s=request_timeout_s,
            undock_timeout_s=cfg.undock_timeout_seconds,
            undock_no_track_timeout_s=cfg.undock_no_track_timeout_seconds,
            settle_s=settle_s,
            galaxy_map_settle_s=galaxy_map_settle_s,
            supercruise_exit_settle_s=cfg.dock_supercruise_exit_settle_seconds,
            boost_settle_s=boost_settle_s,
            deny_retry_delay_s=deny_retry_delay_s,
            mass_lock_boost_delay_s=cfg.mass_lock_boost_delay_seconds,
            nav_panel_open_delay_s=cfg.haul_two_way_nav_panel_open_delay_seconds,
        ),
        travel=RoutineTravelSettings(
            auto_hyperspace_engage=cfg.haul_two_way_auto_hyperspace_engage,
            open_nav_panel_after_hyperspace_arrival=cfg.haul_two_way_open_nav_panel_after_hyperspace_arrival,
            max_dock_retries=3,
        ),
        time_fn=time_fn,
        sleeper=sleeper,
        progress_fn=progress_fn,
        announce_fn=announce_fn if announce_fn is not None else app._announce_tts,
    )
