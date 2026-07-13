from __future__ import annotations

from dataclasses import dataclass

from edap.actions import ActionDispatchResult
from edap.routines._base import RoutineResult
from edap.routines.runtime import RoutineRuntime
from edap.routines.transit import (
    depart_system_to_route,
    is_manual_landing_result,
    read_ship_position,
    set_galaxy_map_destination_for_transit,
    should_set_galaxy_map_destination,
    transit_to_station,
    undock_and_route_to_system,
    wait_for_arrival_or_approach_event,
)
from edap.tts import AnnouncementId


@dataclass(frozen=True)
class TravelDestination:
    system: str
    station: str = ""
    on_land: bool = False

    @property
    def label(self) -> str:
        return f"{self.station} ({self.system})" if self.station and self.system else self.station or self.system


def travel_to_station(runtime: RoutineRuntime, *, destination: TravelDestination) -> RoutineResult:
    if not destination.system.strip():
        raise ValueError("travel destination system is required")

    position = read_ship_position(runtime.journal_dir)
    current_label = position.station or position.system or "current location"
    runtime.progress_fn(
        "Travel phase detect: "
        f"status={position.status}, station={position.station!r}, system={position.system!r}, "
        f"target={destination.label!r}"
    )
    if not destination.station.strip() and _same_system(position.system, destination.system):
        return _travel_system_arrival(runtime, destination, assume_arrived=True)

    if position.status == "docked":
        result = undock_and_route_to_system(
            runtime,
            current_label=current_label,
            current_system=position.system,
            destination_system=destination.system,
            routine_name="travel",
        )
        if result.dispatch.status != "ok":
            return result
        if not destination.station.strip():
            return _travel_system_arrival(
                runtime,
                destination,
                assume_arrived=_same_system(position.system, destination.system),
            )
        return _travel_transit(runtime, destination, assume_arrived=False)

    if position.status == "normal_space":
        result = depart_system_to_route(
            runtime,
            current_label=current_label,
            current_system=position.system,
            destination_system=destination.system,
            routine_name="travel",
        )
        if result.dispatch.status != "ok":
            return result
        if not destination.station.strip():
            return _travel_system_arrival(
                runtime,
                destination,
                assume_arrived=_same_system(position.system, destination.system),
            )
        return _travel_transit(
            runtime,
            destination,
            assume_arrived=_same_system(position.system, destination.system),
        )

    if position.status == "supercruise":
        if should_set_galaxy_map_destination(
            current_system=position.system,
            destination_system=destination.system,
        ):
            route_confirmed = _set_route_from_supercruise(runtime, destination.system)
            if route_confirmed:
                runtime.progress_fn("Route confirmed from supercruise - engaging hyperspace...")
                runtime.announce_fn(AnnouncementId.STATION_CLEARED)
                runtime.controls.hyper_super_combination()
            else:
                runtime.progress_fn("Skipping automatic FSD engage because the galaxy-map route is unconfirmed.")
        if not destination.station.strip():
            return _travel_system_arrival(
                runtime,
                destination,
                assume_arrived=_same_system(position.system, destination.system),
            )
        return _travel_transit(
            runtime,
            destination,
            assume_arrived=_same_system(position.system, destination.system),
        )

    runtime.progress_fn("Travel start location is unknown; waiting for route or approach journal events.")
    if not destination.station.strip():
        return _travel_system_arrival(runtime, destination, assume_arrived=False)
    return _travel_transit(runtime, destination, assume_arrived=False)


def _travel_system_arrival(
    runtime: RoutineRuntime,
    destination: TravelDestination,
    *,
    assume_arrived: bool,
) -> RoutineResult:
    if assume_arrived:
        runtime.progress_fn(f"Already in {destination.system} system; travel complete.")
    else:
        runtime.progress_fn(f"Waiting for hyperspace arrival in {destination.system} system...")
        arrival_observed, pending_events = wait_for_arrival_or_approach_event(
            runtime.watcher,
            destination_system=destination.system,
            deadline=runtime.time_fn() + runtime.timing.dock_timeout_s,
            time_fn=runtime.time_fn,
        )
        if not arrival_observed and not pending_events:
            return RoutineResult(
                action="travel",
                dispatch=ActionDispatchResult(
                    action="travel",
                    status="error",
                    reason=f"timed out waiting for arrival in {destination.system}",
                ),
                details={"system": destination.system, "station": destination.station},
            )
        runtime.progress_fn(f"Arrived in {destination.system} system; travel complete.")
    return RoutineResult(
        action="travel",
        dispatch=ActionDispatchResult(action="travel", status="ok"),
        details={"system": destination.system, "station": destination.station},
    )


def _travel_transit(
    runtime: RoutineRuntime,
    destination: TravelDestination,
    *,
    assume_arrived: bool,
) -> RoutineResult:
    result = transit_to_station(
        runtime,
        destination=destination,
        destination_label=destination.label,
        routine_name="travel",
        assume_arrived_in_destination_system=assume_arrived,
    )
    if is_manual_landing_result(result):
        return result
    if result.dispatch.status == "ok":
        return RoutineResult(
            action="travel",
            dispatch=ActionDispatchResult(action="travel", status="ok", reason=result.dispatch.reason),
            details={
                "system": destination.system,
                "station": destination.station,
                "transit_action": result.action,
            },
        )
    return result


def _set_route_from_supercruise(runtime: RoutineRuntime, destination_system: str) -> bool:
    runtime.progress_fn(f"Setting galaxy map destination: {destination_system}...")
    return set_galaxy_map_destination_for_transit(
        runtime=runtime,
        destination_system=destination_system,
        routine_name="travel",
    )


def _same_system(left: str, right: str) -> bool:
    return bool(left.strip()) and left.strip().lower() == right.strip().lower()
