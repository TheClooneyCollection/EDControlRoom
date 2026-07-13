"""Neutron travel routine launcher."""
from __future__ import annotations

from rich.markup import escape

from edap.control_room.history import now_iso
from edap.control_room.interfaces import TravelHost
from edap.control_room.routine_runtime_builder import build_routine_runtime
from edap.control_room_state import CommandHistoryEntry
from edap.routines.spansh_route import fly_spansh_route
from edap.routing.types import Route


def dispatch_spansh_route(
    app: TravelHost,
    *,
    route: Route,
    station: str = "",
    skip_delay: bool = False,
    raw_command: str | None = None,
) -> None:
    if not app._check_routine_ready():
        return
    station = (station or "").strip()

    progress = app._make_progress()
    controls = app._make_controls(progress)
    watcher = app._make_watcher()
    sleeper = app._make_sleeper()
    runtime = build_routine_runtime(
        app,
        controls=controls,
        watcher=watcher,
        sleeper=sleeper,
        time_fn=app._time_fn,
        progress_fn=progress,
        dock_timeout_s=app._config.controls.haul_dock_timeout_seconds,
        galaxy_map_settle_s=app._config.controls.galaxy_map_settle_seconds,
    )

    destination_system = route.destination_system or (route.waypoints[-1].system if route.waypoints else "")

    app._record_history_entry(CommandHistoryEntry(
        raw=raw_command or _spansh_raw_command(destination_system=destination_system, station=station, skip_delay=skip_delay),
        command="spansh_route",
        params={
            "destination_system": destination_system,
            "station": station,
            "waypoint_count": str(len(route.waypoints)),
        },
        timestamp=now_iso(),
    ))

    app._start_delayed_routine(
        description=_spansh_description(destination_system=destination_system, station=station),
        start_message=_spansh_start_message(destination_system=destination_system, station=station),
        skip_delay=skip_delay,
        fn=lambda: fly_spansh_route(runtime, route=route, station=station),
        active_routine_name="spansh_route",
    )


def _spansh_raw_command(*, destination_system: str, station: str, skip_delay: bool) -> str:
    prefix = "!" if skip_delay else ""
    if station:
        return f"{prefix}spansh {destination_system} / {station}"
    return f"{prefix}spansh {destination_system}"


def _spansh_description(*, destination_system: str, station: str) -> str:
    if station:
        return f"spansh route to {destination_system} / {station}"
    return f"spansh route to {destination_system}"


def _spansh_start_message(*, destination_system: str, station: str) -> str:
    if station:
        return (
            f"Starting Spansh route to [cyan]{escape(destination_system)}[/] "
            f"then docking at [cyan]{escape(station)}[/]"
        )
    return f"Starting Spansh route to [cyan]{escape(destination_system)}[/]"
