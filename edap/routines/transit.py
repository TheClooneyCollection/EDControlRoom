from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Protocol

from edap.actions import ActionDispatchResult
from edap.routines._base import RoutineResult, SupportsRoutineControls, SupportsPollEvents, _is_in_supercruise_event
from edap.routines.callbacks import AnnouncementCallback, ProgressCallback
from edap.routines.docking import _undock_until_undocked, _wait_for_clear_of_station, dock, station_refuel_menu
from edap.routines.escape import escape_mass_lock
from edap.routines.galaxy_map import set_gal_map_destination
from edap.state import get_latest_journal_log, read_ship_state
from edap.tts import AnnouncementId


class TransitDestination(Protocol):
    station: str
    system: str
    on_land: bool


class TransitTiming(Protocol):
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


class TransitTravelSettings(Protocol):
    auto_hyperspace_engage: bool
    open_nav_panel_after_hyperspace_arrival: bool
    max_dock_retries: int


class TransitRuntime(Protocol):
    controls: SupportsRoutineControls
    watcher: SupportsPollEvents
    journal_dir: Path
    timing: TransitTiming
    travel: TransitTravelSettings
    time_fn: Callable[[], float]
    sleeper: Callable[[float], None]
    progress_fn: ProgressCallback
    announce_fn: AnnouncementCallback


class TransitResumeState(Enum):
    NONE = auto()
    ARRIVED_IN_DESTINATION_SYSTEM = auto()
    POST_DROP_NEAR_STATION = auto()
    AWAITING_DOCKED = auto()


@dataclass(frozen=True)
class ShipPosition:
    status: str
    station: str
    system: str


MANUAL_LANDING_REASON = "manual landing required"


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


def read_market_station(journal_dir: Path) -> tuple[str, str]:
    market_path = journal_dir / "Market.json"
    try:
        with market_path.open(encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return "", ""
    return str(data.get("StationName", "")), str(data.get("StarSystem", ""))


def read_ship_position(journal_dir: Path) -> ShipPosition:
    ship_status = "unknown"
    current_station = ""
    current_system = ""
    log_path = get_latest_journal_log(journal_dir)
    if log_path is not None:
        try:
            state = read_ship_state(log_path)
        except Exception:
            state = None
        if state is not None:
            current_station = str(state.station or "")
            current_system = str(state.location or "")
            status = str(state.status or "")
            if status == "in_station":
                ship_status = "docked"
            elif status in {"in_space", "in_undocking", "starting_docking", "in_docking"}:
                ship_status = "normal_space"
            elif status in {"in_supercruise", "starting_hyperspace", "starting_supercruise"}:
                ship_status = "supercruise"

    if ship_status in {"docked", "unknown"}:
        market_station, market_system = read_market_station(journal_dir)
        if not current_station and market_station:
            current_station = market_station
        if not current_system and market_system:
            current_system = market_system
        if current_station:
            ship_status = "docked"

    return ShipPosition(status=ship_status, station=current_station, system=current_system)


def detect_transit_resume_state(events: list[dict], destination: TransitDestination) -> TransitResumeState:
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
    destination: TransitDestination,
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


def manual_landing_result(destination: TransitDestination) -> RoutineResult:
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


def should_set_galaxy_map_destination(*, current_system: str, destination_system: str) -> bool:
    current_system_normalized = current_system.strip().lower()
    destination_system_normalized = destination_system.strip().lower()
    if not destination_system_normalized:
        return False
    if current_system_normalized and current_system_normalized == destination_system_normalized:
        return False
    return True


def engage_hyperspace_after_escape(runtime: TransitRuntime, *, progress_message: str) -> None:
    if not runtime.travel.auto_hyperspace_engage:
        return
    runtime.progress_fn(progress_message)
    runtime.announce_fn(AnnouncementId.STATION_CLEARED)
    runtime.controls.hyper_super_combination()


def set_galaxy_map_destination_for_transit(
    *,
    runtime: TransitRuntime,
    destination_system: str,
    routine_name: str,
    max_attempts: int = 2,
    retry_delay_s: float = 1.0,
) -> bool:
    runtime.announce_fn(AnnouncementId.DESTINATION_SET, system_name=destination_system)
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
        f"Set the route manually; {routine_name} will continue after journal arrival events."
    )
    runtime.announce_fn(AnnouncementId.ROUTE_UNCONFIRMED, system_name=destination_system)
    return False


def open_navigation_panel_after_arrival(runtime: TransitRuntime, *, station_name: str = "") -> None:
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


def undock_and_route_to_system(
    runtime: TransitRuntime,
    *,
    current_label: str,
    current_system: str,
    destination_system: str,
    routine_name: str,
) -> RoutineResult:
    runtime.progress_fn(f"Undocking from {current_label}...")
    result, pending_events = _undock_until_undocked(
        runtime.controls,
        runtime.watcher,
        undock_timeout_s=runtime.timing.undock_timeout_s,
        step_delay_s=runtime.timing.step_delay_s,
        time_fn=runtime.time_fn,
        sleeper=runtime.sleeper,
        progress_fn=runtime.progress_fn,
    )
    if result.dispatch.status != "ok":
        return result

    route_confirmed = True
    if should_set_galaxy_map_destination(
        current_system=current_system,
        destination_system=destination_system,
    ):
        runtime.progress_fn(f"Setting galaxy map destination: {destination_system}...")
        route_confirmed = set_galaxy_map_destination_for_transit(
            runtime=runtime,
            destination_system=destination_system,
            routine_name=routine_name,
        )

    clear_result = _wait_for_clear_of_station(
        runtime.watcher,
        undocked_event=result.trigger_event,
        no_track_timeout_s=runtime.timing.undock_no_track_timeout_s,
        time_fn=runtime.time_fn,
        progress_fn=runtime.progress_fn,
        pending_events=pending_events,
    )
    if clear_result.dispatch.status != "ok":
        runtime.progress_fn(
            "Error: "
            f"{clear_result.dispatch.reason}; {routine_name} aborted. You can resume with replay / ctrl-r."
        )
        runtime.announce_fn(AnnouncementId.HAUL_ABORTED)
        return clear_result
    escape_mass_lock(
        runtime.controls,
        journal_dir=runtime.journal_dir,
        step_delay_s=runtime.timing.step_delay_s,
        boost_delay_s=runtime.timing.mass_lock_boost_delay_s,
        sleeper=runtime.sleeper,
        progress_fn=runtime.progress_fn,
    )
    if route_confirmed:
        engage_hyperspace_after_escape(
            runtime,
            progress_message="Mass lock cleared - engaging hyperspace via HyperSuperCombination...",
        )
    else:
        runtime.progress_fn("Skipping automatic FSD engage because the galaxy-map route is unconfirmed.")
    return clear_result if clear_result.dispatch.status == "ok" else result


def depart_system_to_route(
    runtime: TransitRuntime,
    *,
    current_label: str,
    current_system: str,
    destination_system: str,
    routine_name: str,
) -> RoutineResult:
    runtime.progress_fn(f"Departing {current_label} system in normal space...")
    route_confirmed = True
    if should_set_galaxy_map_destination(
        current_system=current_system,
        destination_system=destination_system,
    ):
        runtime.progress_fn(f"Setting galaxy map destination: {destination_system}...")
        route_confirmed = set_galaxy_map_destination_for_transit(
            runtime=runtime,
            destination_system=destination_system,
            routine_name=routine_name,
        )
    escape_mass_lock(
        runtime.controls,
        journal_dir=runtime.journal_dir,
        step_delay_s=runtime.timing.step_delay_s,
        boost_delay_s=runtime.timing.mass_lock_boost_delay_s,
        sleeper=runtime.sleeper,
        progress_fn=runtime.progress_fn,
    )
    if route_confirmed:
        engage_hyperspace_after_escape(
            runtime,
            progress_message="Mass lock cleared - engaging hyperspace via HyperSuperCombination...",
        )
    else:
        runtime.progress_fn("Skipping automatic FSD engage because the galaxy-map route is unconfirmed.")
    return RoutineResult(action="depart_system", dispatch=ActionDispatchResult(action="depart_system", status="ok"))


def transit_to_station(
    runtime: TransitRuntime,
    *,
    destination: TransitDestination,
    destination_label: str,
    routine_name: str,
    assume_arrived_in_destination_system: bool = False,
) -> RoutineResult:
    recent_events = read_latest_journal_events(runtime.journal_dir)
    resume_state = detect_transit_resume_state(recent_events, destination)
    if assume_arrived_in_destination_system and resume_state == TransitResumeState.NONE:
        resume_state = TransitResumeState.ARRIVED_IN_DESTINATION_SYSTEM
    pending_events: list[dict[str, object]] = []
    if resume_state == TransitResumeState.AWAITING_DOCKED:
        runtime.progress_fn(f"Docking already in progress for {destination_label} - waiting for Docked.")
        return station_refuel_menu(
            runtime.controls,
            runtime.watcher,
            dock_timeout_s=runtime.timing.dock_timeout_s,
            settle_s=runtime.timing.settle_s,
            time_fn=runtime.time_fn,
            sleeper=runtime.sleeper,
            progress_fn=runtime.progress_fn,
        )
    if resume_state == TransitResumeState.ARRIVED_IN_DESTINATION_SYSTEM:
        runtime.progress_fn(f"Already in supercruise in {destination_label} system - opening navigation panel.")
    elif resume_state == TransitResumeState.POST_DROP_NEAR_STATION:
        if destination.on_land:
            runtime.progress_fn(f"Already in normal space near on-land {destination_label} - handing off for manual landing.")
        else:
            runtime.progress_fn(f"Already in normal space near {destination_label} - skipping drop wait.")
    else:
        runtime.progress_fn(f"Waiting for hyperspace arrival in {destination_label} system...")

    if resume_state == TransitResumeState.NONE:
        arrival_observed, pending_events = wait_for_arrival_or_approach_event(
            runtime.watcher,
            destination_system=destination.system,
            deadline=runtime.time_fn() + runtime.timing.dock_timeout_s,
            time_fn=runtime.time_fn,
        )
        if not arrival_observed:
            runtime.progress_fn("Warning: hyperspace arrival event not observed; continuing toward station.")
        else:
            runtime.progress_fn("Arrived in destination system")
            open_navigation_panel_after_arrival(runtime, station_name=destination.station)
    elif resume_state == TransitResumeState.ARRIVED_IN_DESTINATION_SYSTEM:
        open_navigation_panel_after_arrival(runtime, station_name=destination.station)

    if destination.on_land:
        if resume_state == TransitResumeState.POST_DROP_NEAR_STATION:
            runtime.progress_fn(
                f"{destination_label} is marked on-land; manual landing required from normal space. "
                f"Resume {routine_name} after landing."
            )
            return manual_landing_result(destination)
        runtime.progress_fn(
            f"{destination_label} is marked on-land; waiting for SupercruiseExit before handing off."
        )
        drop_event = wait_for_on_land_handoff(
            runtime.watcher,
            destination=destination,
            pending_events=pending_events,
            deadline=runtime.time_fn() + runtime.timing.dock_timeout_s,
            time_fn=runtime.time_fn,
        )
        if drop_event is None:
            return RoutineResult(
                action="manual_landing",
                dispatch=ActionDispatchResult(
                    action="manual_landing",
                    status="error",
                    reason=f"timed out waiting for SupercruiseExit near {destination.station}",
                ),
            )
        runtime.progress_fn(
            f"Reached normal space near on-land {destination_label}; manual landing required. "
            f"Resume {routine_name} after landing."
        )
        return manual_landing_result(destination)

    result = dock(
        runtime.controls,
        runtime.watcher,
        wait_for_supercruise_exit=resume_state != TransitResumeState.POST_DROP_NEAR_STATION,
        auto_refuel=True,
        max_retries=runtime.travel.max_dock_retries,
        request_timeout_s=runtime.timing.request_timeout_s,
        dock_timeout_s=runtime.timing.dock_timeout_s,
        settle_s=runtime.timing.settle_s,
        step_delay_s=runtime.timing.step_delay_s,
        supercruise_exit_settle_s=runtime.timing.supercruise_exit_settle_s,
        boost_settle_s=runtime.timing.boost_settle_s,
        deny_retry_delay_s=runtime.timing.deny_retry_delay_s,
        abort_on_interdiction=True,
        time_fn=runtime.time_fn,
        sleeper=runtime.sleeper,
        progress_fn=runtime.progress_fn,
        pending_events=pending_events,
        announce_fn=runtime.announce_fn,
        announce_station_name=destination.station,
    )
    if result.action == "Interdicted" and result.dispatch.status != "ok":
        runtime.progress_fn(
            f"Interdiction detected during {routine_name} transit; {routine_name} aborted. "
            f"Escape or re-enter supercruise, then resume {routine_name}."
        )
        runtime.announce_fn(AnnouncementId.HAUL_ABORTED)
    return result
