"""Travel routine launcher."""
from __future__ import annotations

from rich.markup import escape

from edap.control_room.history import now_iso
from edap.control_room.interfaces import TravelHost
from edap.control_room.routines_haul import _build_haul_runtime
from edap.control_room_state import CommandHistoryEntry
from edap.routines import travel_to_station
from edap.routines.travel import TravelDestination


def cmd_travel(
    app: TravelHost,
    rest: str,
    *,
    skip_delay: bool = False,
    raw_command: str | None = None,
) -> None:
    parsed = parse_travel_command(rest)
    if parsed is None:
        app._log("[red]Usage: travel <system> / <station>[/]")
        return
    system, station = parsed
    dispatch_travel(
        app,
        system=system,
        station=station,
        skip_delay=skip_delay,
        raw_command=raw_command,
    )


def parse_travel_command(rest: str) -> tuple[str, str] | None:
    raw = rest.strip()
    if not raw:
        return None
    for separator in (" / ", " | ", " -- "):
        if separator in raw:
            system, station = raw.split(separator, 1)
            system = system.strip()
            station = station.strip()
            return (system, station) if system and station else None
    return None


def dispatch_travel(
    app: TravelHost,
    *,
    system: str,
    station: str,
    on_land: bool = False,
    skip_delay: bool = False,
    raw_command: str | None = None,
) -> None:
    if not app._check_routine_ready():
        return
    system = system.strip()
    station = station.strip()
    if not system or not station:
        app._log("[red]Travel needs both destination system and station.[/]")
        return

    progress = app._make_progress()
    controls = app._make_controls(progress)
    watcher = app._make_watcher()
    sleeper = app._make_sleeper()
    runtime = _build_haul_runtime(
        app,
        controls=controls,
        watcher=watcher,
        sleeper=sleeper,
        time_fn=app._time_fn,
        progress_fn=progress,
        dock_timeout_s=app._config.controls.haul_dock_timeout_seconds,
        galaxy_map_settle_s=app._config.controls.galaxy_map_settle_seconds,
    )
    destination = TravelDestination(system=system, station=station, on_land=on_land)

    app._record_history_entry(CommandHistoryEntry(
        raw=raw_command or f"{'!' if skip_delay else ''}travel {system} / {station}",
        command="travel",
        params={
            "system": system,
            "station": station,
            "on_land": on_land,
        },
        timestamp=now_iso(),
    ))

    app._start_delayed_routine(
        description=f"travel {system} / {station}",
        start_message=f"Starting travel assist to [cyan]{escape(station)}[/] in [cyan]{escape(system)}[/]",
        skip_delay=skip_delay,
        fn=lambda: travel_to_station(runtime, destination=destination),
        active_routine_name="travel",
    )
