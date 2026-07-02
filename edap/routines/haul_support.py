from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Protocol

from edap.actions import ActionDispatchResult
from edap.cargo_manifest import read_cargo_inventory as read_cargo_inventory_with_retry
from edap.config import MarketBuyHoldSegmentConfig
from edap.routines._base import RoutineResult, SupportsHaulControls, SupportsPollEvents, _is_in_supercruise_event
from edap.routines.callbacks import AnnouncementCallback, ProgressCallback
from edap.routines.galaxy_map import set_gal_map_destination
from edap.tts import AnnouncementId


class HaulDestination(Protocol):
    station: str
    system: str
    on_land: bool


class TransitResumeState(Enum):
    NONE = auto()
    ARRIVED_IN_DESTINATION_SYSTEM = auto()
    POST_DROP_NEAR_STATION = auto()
    AWAITING_DOCKED = auto()


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


MANUAL_LANDING_REASON = "manual landing required"


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


def read_market_station(journal_dir: Path) -> tuple[str, str]:
    market_path = journal_dir / "Market.json"
    try:
        with market_path.open(encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return "", ""
    return str(data.get("StationName", "")), str(data.get("StarSystem", ""))


def sellable_cargo(inventory: list[dict]) -> list[dict]:
    return [
        item for item in inventory
        if item.get("Count", 0) > 0
        and item.get("Stolen", 0) == 0
        and "MissionID" not in item
    ]


def read_latest_journal_events(journal_dir: Path) -> list[dict]:
    journals = sorted(journal_dir.glob("Journal.*.log"), key=lambda p: p.stat().st_mtime)
    if not journals:
        return []
    events: list[dict] = []
    try:
        with journals[-1].open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    except OSError:
        pass
    return events


def detect_transit_resume_state(events: list[dict], destination: HaulDestination) -> TransitResumeState:
    destination_station = destination.station.lower()
    destination_system = destination.system.lower()

    for event in reversed(events):
        evt_name = str(event.get("event", ""))

        if evt_name in {"DockingRequested", "DockingGranted"}:
            station_name = str(event.get("StationName", "")).lower()
            return (
                TransitResumeState.AWAITING_DOCKED
                if destination_station and station_name == destination_station
                else TransitResumeState.NONE
            )

        if evt_name == "SupercruiseExit":
            body_type = str(event.get("BodyType", "")).lower()
            system_name = str(event.get("StarSystem", "")).lower()
            if not destination.on_land and body_type != "station":
                return TransitResumeState.NONE
            return (
                TransitResumeState.POST_DROP_NEAR_STATION
                if not destination_system or not system_name or system_name == destination_system
                else TransitResumeState.NONE
            )

        if evt_name in {"SupercruiseEntry", "FSDJump"}:
            system_name = str(event.get("StarSystem", "")).lower()
            return (
                TransitResumeState.ARRIVED_IN_DESTINATION_SYSTEM
                if not destination_system or not system_name or system_name == destination_system
                else TransitResumeState.NONE
            )

        if evt_name == "Undocked":
            return TransitResumeState.NONE

    return TransitResumeState.NONE


def wait_for_arrival_or_approach_event(
    watcher: SupportsPollEvents,
    *,
    destination_system: str,
    deadline: float,
    time_fn: Callable[[], float],
) -> tuple[bool, list[dict[str, object]]]:
    approach_events = {"SupercruiseExit", "DockingRequested", "DockingGranted", "Docked"}
    destination_system_lower = destination_system.lower()
    while time_fn() <= deadline:
        batch = watcher.poll()
        for index, event in enumerate(batch):
            if _is_in_supercruise_event(event):
                system_name = str(event.get("StarSystem", "")).lower()
                if destination_system_lower and system_name and system_name != destination_system_lower:
                    continue
                return True, batch[index + 1:]
            if event.get("event") in approach_events:
                return False, batch[index:]
    return False, []


def wait_for_on_land_handoff(
    watcher: SupportsPollEvents,
    *,
    destination: HaulDestination,
    pending_events: list[dict[str, object]],
    deadline: float,
    time_fn: Callable[[], float],
) -> dict[str, object] | None:
    queued_events = list(pending_events)
    destination_system_lower = destination.system.lower()
    while time_fn() <= deadline:
        batch = queued_events if queued_events else watcher.poll()
        queued_events = []
        for event in batch:
            if event.get("event") != "SupercruiseExit":
                continue
            system_name = str(event.get("StarSystem", "")).lower()
            if destination_system_lower and system_name and system_name != destination_system_lower:
                continue
            return event
    return None


def manual_landing_result(destination: HaulDestination) -> RoutineResult:
    return RoutineResult(
        action="manual_landing",
        dispatch=ActionDispatchResult(
            action="manual_landing",
            status="ok",
            reason=MANUAL_LANDING_REASON,
        ),
        details={
            "station": destination.station,
            "system": destination.system,
            "on_land": True,
        },
    )


def is_manual_landing_result(result: RoutineResult | None) -> bool:
    return result is not None and result.dispatch.reason == MANUAL_LANDING_REASON


def engage_hyperspace_after_escape(runtime: HaulRuntime, *, progress_message: str) -> None:
    if not runtime.travel.auto_hyperspace_engage:
        return
    runtime.progress_fn(progress_message)
    runtime.announce_fn(AnnouncementId.STATION_CLEARED)
    runtime.controls.hyper_super_combination()


def set_galaxy_map_destination_for_haul(
    *,
    runtime: HaulRuntime,
    destination_system: str,
    max_attempts: int = 2,
    retry_delay_s: float = 1.0,
) -> bool:
    for attempt in range(1, max_attempts + 1):
        result = set_gal_map_destination(
            runtime.controls,
            destination=destination_system,
            journal_dir=runtime.journal_dir,
            step_delay_s=runtime.timing.step_delay_s,
            map_settle_s=runtime.timing.galaxy_map_settle_s,
            sleeper=runtime.sleeper,
            progress_fn=runtime.progress_fn,
        )
        if result.dispatch.status == "ok":
            return True

        reason = result.dispatch.reason or result.dispatch.status
        runtime.progress_fn(
            f"Warning: galaxy map route to {destination_system} was not confirmed "
            f"(attempt {attempt}/{max_attempts}: {reason})."
        )
        if attempt < max_attempts and retry_delay_s > 0:
            runtime.sleeper(retry_delay_s)

    runtime.progress_fn(
        f"Warning: route to {destination_system} is unconfirmed. "
        "Set the route manually; haul will continue after journal arrival events."
    )
    runtime.announce_fn(AnnouncementId.ROUTE_UNCONFIRMED, system_name=destination_system)
    return False


def open_navigation_panel_after_arrival(runtime: HaulRuntime, *, station_name: str = "") -> None:
    if not runtime.travel.open_nav_panel_after_hyperspace_arrival:
        return
    if runtime.timing.nav_panel_open_delay_s > 0:
        runtime.progress_fn(
            f"Waiting {runtime.timing.nav_panel_open_delay_s:.1f}s before opening navigation panel..."
        )
        runtime.sleeper(runtime.timing.nav_panel_open_delay_s)
    if station_name:
        runtime.announce_fn(AnnouncementId.ARRIVAL_NEXT_STATION, station_name=station_name)
    runtime.progress_fn("Hyperspace complete - opening left panel for navigation...")
    dispatch = runtime.controls.focus_left_panel()
    if dispatch.status != "ok":
        runtime.progress_fn(f"Warning: could not open left panel ({dispatch.reason or dispatch.status}); continuing")
