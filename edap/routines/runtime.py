"""Shared runtime types used by all routines (haul, travel, spansh route)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from edap.routines._base import SupportsRoutineControls, SupportsPollEvents
from edap.routines.callbacks import AnnouncementCallback, ProgressCallback


@dataclass(frozen=True)
class RoutineTiming:
    step_delay_s: float
    dock_timeout_s: float
    request_timeout_s: float
    undock_timeout_s: float
    undock_no_track_timeout_s: float
    settle_s: float
    galaxy_map_settle_s: float
    supercruise_exit_settle_s: float
    boost_settle_s: float
    deny_retry_delay_s: float
    mass_lock_boost_delay_s: float
    nav_panel_open_delay_s: float


@dataclass(frozen=True)
class RoutineTravelSettings:
    auto_hyperspace_engage: bool
    open_nav_panel_after_hyperspace_arrival: bool
    max_dock_retries: int


@dataclass
class RoutineRuntime:
    controls: SupportsRoutineControls
    watcher: SupportsPollEvents
    journal_dir: Path
    timing: RoutineTiming
    travel: RoutineTravelSettings
    time_fn: Callable[[], float]
    sleeper: Callable[[float], None]
    progress_fn: ProgressCallback
    announce_fn: AnnouncementCallback
