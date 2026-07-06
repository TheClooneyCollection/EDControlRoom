from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from edap.cargo_manifest import read_cargo_inventory as read_cargo_inventory_with_retry
from edap.config import MarketBuyHoldSegmentConfig
from edap.routines._base import SupportsHaulControls, SupportsPollEvents
from edap.routines.callbacks import AnnouncementCallback, ProgressCallback


@dataclass(frozen=True)
class HaulTiming:
    step_delay_s: float
    max_hold_s: float
    dock_timeout_s: float
    request_timeout_s: float
    undock_timeout_s: float
    undock_no_track_timeout_s: float
    trade_timeout_s: float
    settle_s: float
    galaxy_map_settle_s: float
    supercruise_exit_settle_s: float
    boost_settle_s: float
    deny_retry_delay_s: float
    mass_lock_boost_delay_s: float
    post_sell_settle_s: float
    nav_panel_open_delay_s: float


@dataclass(frozen=True)
class HaulMarketSettings:
    buy_hold_segments: tuple[MarketBuyHoldSegmentConfig, ...]
    sell_quantity_restore_taps: int
    sell_quantity_restore_tap_delay_s: float
    critical_level_multiplier: float


@dataclass(frozen=True)
class HaulTravelSettings:
    auto_hyperspace_engage: bool
    open_nav_panel_after_hyperspace_arrival: bool
    max_dock_retries: int


@dataclass
class HaulRuntime:
    controls: SupportsHaulControls
    watcher: SupportsPollEvents
    journal_dir: Path
    market_path: Path
    timing: HaulTiming
    market: HaulMarketSettings
    travel: HaulTravelSettings
    time_fn: Callable[[], float]
    sleeper: Callable[[float], None]
    progress_fn: ProgressCallback
    announce_fn: AnnouncementCallback


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
