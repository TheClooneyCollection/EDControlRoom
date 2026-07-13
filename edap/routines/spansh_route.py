"""Neutron travel routine: coordinate a per-waypoint Spansh route.

The routine does not fly the ship. For the first hop it handles the same
undock / depart-normal-space handoff that `travel` does so operators can
dispatch it from any start state. After that it sets each next waypoint in
the galaxy map for the operator, waits (indefinitely) for arrival via
journal events, and repeats until the final waypoint. Optional station is
handed off to `transit_to_station` after final-system arrival so trade
routes can flow end-to-end.
"""
from __future__ import annotations

import math

from edap.actions import ActionDispatchResult
from edap.routines._base import RoutineResult
from edap.routines.runtime import RoutineRuntime
from edap.routines.transit import (
    depart_system_to_route,
    read_ship_position,
    set_galaxy_map_destination_for_transit,
    transit_to_station,
    undock_and_route_to_system,
    wait_for_arrival_or_approach_event,
)
from edap.routines.travel import TravelDestination
from edap.routing.types import Route, RouteWaypoint
from edap.tts import AnnouncementId


_ROUTINE_NAME = "spansh_route"


def fly_spansh_route(
    runtime: RoutineRuntime,
    *,
    route: Route,
    station: str = "",
) -> RoutineResult:
    waypoints = route.waypoints
    if len(waypoints) < 2:
        return RoutineResult(
            action=_ROUTINE_NAME,
            dispatch=ActionDispatchResult(
                action=_ROUTINE_NAME,
                status="error",
                reason="route must contain at least a source and one destination waypoint",
            ),
        )

    first_waypoint = waypoints[1]
    position = read_ship_position(runtime.journal_dir)
    runtime.progress_fn(
        "Spansh phase detect: "
        f"status={position.status}, station={position.station!r}, system={position.system!r}, "
        f"first_waypoint={first_waypoint.system!r}"
    )

    first_hop_result: RoutineResult | None = None
    if position.status == "docked":
        current_label = position.station or position.system or "current location"
        first_hop_result = undock_and_route_to_system(
            runtime,
            current_label=current_label,
            current_system=position.system,
            destination_system=first_waypoint.system,
            routine_name=_ROUTINE_NAME,
        )
    elif position.status == "normal_space":
        current_label = position.station or position.system or "current location"
        first_hop_result = depart_system_to_route(
            runtime,
            current_label=current_label,
            current_system=position.system,
            destination_system=first_waypoint.system,
            routine_name=_ROUTINE_NAME,
        )

    if first_hop_result is not None:
        if first_hop_result.dispatch.status != "ok":
            return first_hop_result
        if first_waypoint.neutron_boost:
            runtime.announce_fn(
                AnnouncementId.SPANSH_NEUTRON_WAYPOINT_SET,
                system_name=first_waypoint.system,
            )
        _wait_for_waypoint_arrival(runtime, first_waypoint)
        remaining = waypoints[2:]
        loop_offset = 2
    else:
        remaining = waypoints[1:]
        loop_offset = 1

    total = len(waypoints) - 1
    for offset, next_waypoint in enumerate(remaining):
        index = loop_offset + offset
        runtime.progress_fn(
            f"Spansh waypoint {index}/{total}: setting galaxy map to {next_waypoint.system}."
        )
        set_galaxy_map_destination_for_transit(
            runtime=runtime,
            destination_system=next_waypoint.system,
            routine_name=_ROUTINE_NAME,
        )
        if next_waypoint.neutron_boost:
            runtime.announce_fn(
                AnnouncementId.SPANSH_NEUTRON_WAYPOINT_SET,
                system_name=next_waypoint.system,
            )
        _wait_for_waypoint_arrival(runtime, next_waypoint)

    final_system = waypoints[-1].system
    if station.strip():
        destination = TravelDestination(system=final_system, station=station.strip())
        result = transit_to_station(
            runtime,
            destination=destination,
            destination_label=destination.label,
            routine_name=_ROUTINE_NAME,
            assume_arrived_in_destination_system=True,
        )
        return result

    runtime.announce_fn(AnnouncementId.SPANSH_ROUTE_COMPLETE, system_name=final_system)
    return RoutineResult(
        action=_ROUTINE_NAME,
        dispatch=ActionDispatchResult(action=_ROUTINE_NAME, status="ok"),
        details={"destination_system": final_system},
    )


def _wait_for_waypoint_arrival(runtime: RoutineRuntime, waypoint: RouteWaypoint) -> None:
    # No deadline: operator drives every hop and can pause / stop / resume via
    # existing routine controls. JournalWatcher.poll() paces internally.
    wait_for_arrival_or_approach_event(
        runtime.watcher,
        destination_system=waypoint.system,
        deadline=math.inf,
        time_fn=runtime.time_fn,
    )
