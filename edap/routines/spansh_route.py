"""Neutron travel routine: coordinate a per-waypoint Spansh route.

The routine does not fly the ship. It sets the next waypoint in the galaxy
map for the operator, waits for arrival via journal events, and repeats until
the final waypoint. Optional station is handed off to `transit_to_station`
after final-system arrival so trade routes can flow end-to-end.
"""
from __future__ import annotations

from edap.actions import ActionDispatchResult
from edap.routines._base import RoutineResult
from edap.routines.runtime import RoutineRuntime
from edap.routines.transit import (
    set_galaxy_map_destination_for_transit,
    transit_to_station,
    wait_for_arrival_or_approach_event,
)
from edap.routines.travel import TravelDestination
from edap.routing.types import Route
from edap.tts import AnnouncementId


_ROUTINE_NAME = "spansh_route"


def fly_spansh_route(
    runtime: RoutineRuntime,
    *,
    route: Route,
    station: str = "",
    per_hop_timeout_s: float | None = None,
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

    hop_timeout = per_hop_timeout_s if per_hop_timeout_s is not None else runtime.timing.dock_timeout_s

    remaining = waypoints[1:]
    for index, next_waypoint in enumerate(remaining):
        runtime.progress_fn(
            f"Spansh waypoint {index + 1}/{len(remaining)}: setting galaxy map to {next_waypoint.system}."
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
        deadline = runtime.time_fn() + hop_timeout
        arrival_observed, _ = wait_for_arrival_or_approach_event(
            runtime.watcher,
            destination_system=next_waypoint.system,
            deadline=deadline,
            time_fn=runtime.time_fn,
        )
        if not arrival_observed:
            runtime.progress_fn(
                f"Spansh routine timed out waiting for arrival in {next_waypoint.system}."
            )
            return RoutineResult(
                action=_ROUTINE_NAME,
                dispatch=ActionDispatchResult(
                    action=_ROUTINE_NAME,
                    status="error",
                    reason=f"timed out waiting for arrival in {next_waypoint.system}",
                ),
                details={
                    "waypoint_index": index + 1,
                    "waypoint_system": next_waypoint.system,
                },
            )

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
