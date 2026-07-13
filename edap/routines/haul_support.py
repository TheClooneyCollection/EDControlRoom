from __future__ import annotations

import json
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Callable

from edap.cargo_manifest import read_cargo_inventory as read_cargo_inventory_with_retry
from edap.config import MarketBuyHoldSegmentConfig
from edap.routines._base import SupportsPollEvents, SupportsRoutineControls
from edap.routines.callbacks import AnnouncementCallback, ProgressCallback
from edap.routines.runtime import RoutineRuntime, RoutineTiming, RoutineTravelSettings


@dataclass(frozen=True)
class HaulTiming:
    routine: RoutineTiming
    max_hold_s: float
    trade_timeout_s: float
    post_sell_settle_s: float

    # Forwarded read access so existing haul code keeps `timing.step_delay_s` etc.
    @property
    def step_delay_s(self) -> float: return self.routine.step_delay_s
    @property
    def dock_timeout_s(self) -> float: return self.routine.dock_timeout_s
    @property
    def request_timeout_s(self) -> float: return self.routine.request_timeout_s
    @property
    def undock_timeout_s(self) -> float: return self.routine.undock_timeout_s
    @property
    def undock_no_track_timeout_s(self) -> float: return self.routine.undock_no_track_timeout_s
    @property
    def settle_s(self) -> float: return self.routine.settle_s
    @property
    def galaxy_map_settle_s(self) -> float: return self.routine.galaxy_map_settle_s
    @property
    def supercruise_exit_settle_s(self) -> float: return self.routine.supercruise_exit_settle_s
    @property
    def boost_settle_s(self) -> float: return self.routine.boost_settle_s
    @property
    def deny_retry_delay_s(self) -> float: return self.routine.deny_retry_delay_s
    @property
    def mass_lock_boost_delay_s(self) -> float: return self.routine.mass_lock_boost_delay_s
    @property
    def nav_panel_open_delay_s(self) -> float: return self.routine.nav_panel_open_delay_s


@dataclass(frozen=True)
class HaulMarketSettings:
    buy_hold_segments: tuple[MarketBuyHoldSegmentConfig, ...]
    sell_quantity_restore_taps: int
    sell_quantity_restore_tap_delay_s: float
    critical_level_multiplier: float


# Re-export for callers still importing HaulTravelSettings from haul_support.
HaulTravelSettings = RoutineTravelSettings


@dataclass
class HaulRuntime:
    routine: RoutineRuntime
    market_path: Path
    market: HaulMarketSettings
    haul_timing: HaulTiming

    # Forwarded access so existing haul code keeps `runtime.controls`, etc.
    @property
    def controls(self) -> SupportsRoutineControls: return self.routine.controls
    @property
    def watcher(self) -> SupportsPollEvents: return self.routine.watcher
    @property
    def journal_dir(self) -> Path: return self.routine.journal_dir
    @property
    def timing(self) -> HaulTiming: return self.haul_timing
    @property
    def travel(self) -> RoutineTravelSettings: return self.routine.travel
    @property
    def time_fn(self) -> Callable[[], float]: return self.routine.time_fn
    @property
    def sleeper(self) -> Callable[[float], None]: return self.routine.sleeper
    @property
    def progress_fn(self) -> ProgressCallback: return self.routine.progress_fn
    @property
    def announce_fn(self) -> AnnouncementCallback: return self.routine.announce_fn


_ROUTINE_TIMING_FIELDS = tuple(f.name for f in fields(RoutineTiming))
_HAUL_TIMING_EXTRA_FIELDS = ("max_hold_s", "trade_timeout_s", "post_sell_settle_s")


def build_haul_timing(**kwargs: float) -> HaulTiming:
    """Construct HaulTiming from a flat mapping of every timing field."""
    routine_kwargs = {name: kwargs[name] for name in _ROUTINE_TIMING_FIELDS}
    extra_kwargs = {name: kwargs[name] for name in _HAUL_TIMING_EXTRA_FIELDS}
    return HaulTiming(routine=RoutineTiming(**routine_kwargs), **extra_kwargs)


def build_haul_runtime(
    *,
    controls: SupportsRoutineControls,
    watcher: SupportsPollEvents,
    journal_dir: Path,
    market_path: Path,
    timing: HaulTiming,
    market: HaulMarketSettings,
    travel: RoutineTravelSettings,
    time_fn: Callable[[], float],
    sleeper: Callable[[float], None],
    progress_fn: ProgressCallback,
    announce_fn: AnnouncementCallback,
) -> HaulRuntime:
    """Construct a HaulRuntime from flat kwargs, wrapping shared bits in RoutineRuntime."""
    routine = RoutineRuntime(
        controls=controls,
        watcher=watcher,
        journal_dir=journal_dir,
        timing=timing.routine,
        travel=travel,
        time_fn=time_fn,
        sleeper=sleeper,
        progress_fn=progress_fn,
        announce_fn=announce_fn,
    )
    return HaulRuntime(
        routine=routine,
        market_path=market_path,
        market=market,
        haul_timing=timing,
    )


def read_cargo_json(journal_dir: Path) -> list[dict]:
    return read_cargo_inventory_with_retry(journal_dir)


def read_last_cargo_capacity(journal_dir: Path) -> int | None:
    journals = sorted(journal_dir.glob("Journal.*.log"), key=lambda p: p.stat().st_mtime)
    for journal_file in reversed(journals):
        try:
            with journal_file.open(encoding="utf-8") as fh:
                lines = fh.readlines()
        except OSError:
            continue
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            cargo_capacity = event.get("CargoCapacity")
            if isinstance(cargo_capacity, bool) or not isinstance(cargo_capacity, (int, float)):
                continue
            if cargo_capacity > 0:
                return int(cargo_capacity)
    return None


def sellable_cargo(inventory: list[dict]) -> list[dict]:
    return [
        item for item in inventory
        if item.get("Count", 0) > 0
        and item.get("Stolen", 0) == 0
        and "MissionID" not in item
    ]
