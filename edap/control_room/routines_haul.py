"""Haul routine launchers."""
from __future__ import annotations

from pathlib import Path

from rich.markup import escape

from edap.control_room import error_text
from edap.control_room.history import now_iso
from edap.control_room.interfaces import HaulHost
from edap.control_room.models import TradeRoutesData
from edap.control_room_state import CommandHistoryEntry
from edap.haul_config import DEFAULT_HAUL_CONFIG_PATH, HaulConfigError, load_haul_config
from edap.inara.trade_routes import (
    TradeRoute,
    build_trade_routes_url,
    parse_trade_routes_url,
    search_trade_routes,
)
from edap.multi_leg_haul import load_multi_leg_haul_definition
from edap.routines import haul_loop_two_way, multi_leg_haul
from edap.routines.haul_support import HaulMarketSettings, HaulRuntime, HaulTiming, HaulTravelSettings
from edap.routines.haul_two_way import StationLeg, TwoWayHaulRoute


def _haul_param_as_bool(value: str, *, default: bool = False) -> bool:
    raw = value.strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "y", "yes", "land", "surface"}


def _build_haul_runtime(
    app: HaulHost,
    *,
    controls,
    watcher,
    sleeper,
    time_fn,
    progress_fn,
    dock_timeout_s: float,
    galaxy_map_settle_s: float,
    request_timeout_s: float = 20.0,
    trade_timeout_s: float = 30.0,
    settle_s: float = 2.0,
    boost_settle_s: float = 3.0,
    deny_retry_delay_s: float = 5.0,
) -> HaulRuntime:
    cfg = app._config.controls
    return HaulRuntime(
        controls=controls,
        watcher=watcher,
        journal_dir=app._journal_dir,
        market_path=app._journal_dir / "Market.json",
        timing=HaulTiming(
            step_delay_s=cfg.step_delay_seconds,
            max_hold_s=cfg.market_buy_max_hold_seconds,
            dock_timeout_s=dock_timeout_s,
            request_timeout_s=request_timeout_s,
            undock_timeout_s=cfg.undock_timeout_seconds,
            undock_no_track_timeout_s=cfg.undock_no_track_timeout_seconds,
            trade_timeout_s=trade_timeout_s,
            settle_s=settle_s,
            galaxy_map_settle_s=galaxy_map_settle_s,
            supercruise_exit_settle_s=cfg.dock_supercruise_exit_settle_seconds,
            boost_settle_s=boost_settle_s,
            deny_retry_delay_s=deny_retry_delay_s,
            mass_lock_boost_delay_s=cfg.mass_lock_boost_delay_seconds,
            post_sell_settle_s=cfg.haul_post_sell_settle_seconds,
            nav_panel_open_delay_s=cfg.haul_two_way_nav_panel_open_delay_seconds,
        ),
        market=HaulMarketSettings(
            buy_hold_segments=cfg.market_buy_hold_segments,
            sell_quantity_restore_taps=cfg.market_sell_quantity_restore_taps,
            sell_quantity_restore_tap_delay_s=cfg.market_sell_quantity_restore_tap_delay_seconds,
            critical_level_multiplier=cfg.market_critical_level_multiplier,
        ),
        travel=HaulTravelSettings(
            auto_hyperspace_engage=cfg.haul_two_way_auto_hyperspace_engage,
            open_nav_panel_after_hyperspace_arrival=cfg.haul_two_way_open_nav_panel_after_hyperspace_arrival,
            max_dock_retries=3,
        ),
        time_fn=time_fn,
        sleeper=sleeper,
        progress_fn=progress_fn,
        announce_fn=app._announce_tts,
    )


def cmd_haul(
    app: HaulHost,
    rest: str,
    *,
    skip_delay: bool = False,
    raw_command: str | None = None,
) -> None:
    station_1_buying = rest.strip()
    parts = station_1_buying.split(None, 1)
    if parts and parts[0].lower() == "route":
        route_index_raw = parts[1].strip() if len(parts) > 1 else ""
        if not route_index_raw:
            app._log("[red]Usage: haul route <result-number>[/]")
            return
        try:
            route_index = int(route_index_raw)
        except ValueError:
            app._log("[red]Route number must be an integer.[/]")
            return
        load_haul_from_trade_route(
            app,
            route_index=route_index,
            skip_delay=skip_delay,
            raw_command=raw_command or f"{'!' if skip_delay else ''}haul route {route_index}".strip(),
        )
        return
    if parts and parts[0].lower() == "search":
        if app._routine_active:
            app._log("[yellow]A routine is already running — wait for it to finish[/]")
            return
        search_rest = parts[1].strip() if len(parts) > 1 else ""
        if search_rest.lower().startswith("url "):
            query_url = search_rest[4:].strip()
            if not query_url:
                app._log("[red]Usage: haul search url <inara-url>[/]")
                return
            try:
                system_name, query_params = parse_trade_routes_url(query_url)
            except ValueError as exc:
                app._log(f"[red]{escape(str(exc))}[/]")
                return
            dispatch_haul_search(
                app,
                system_name=system_name,
                query_params=query_params,
                skip_delay=skip_delay,
                raw_command=raw_command or f"{'!' if skip_delay else ''}haul search url {query_url}".strip(),
            )
            return
        if search_rest.lower() == "home":
            system_name = app._config.control_room.home_system.strip()
            if not system_name:
                app._log(f"[red]{escape(error_text.render(app._config, 'home_not_set'))}[/]")
                return
        else:
            system_name = search_rest if search_rest else (app._ship.system or "").strip()
        if not system_name:
            app._log("[red]haul search needs a system name, or the current ship system must be known.[/]")
            return
        app._start_haul_search_prompt(
            system_name=system_name,
            seed=None,
            skip_delay=skip_delay,
            raw_command=raw_command or f"{'!' if skip_delay else ''}haul search {system_name}".strip(),
        )
        return
    if not app._check_routine_ready():
        return
    if parts and parts[0].lower() == "load":
        source = Path(parts[1].strip()) if len(parts) > 1 and parts[1].strip() else DEFAULT_HAUL_CONFIG_PATH
        try:
            app._haul_params = load_haul_config(source)
        except (FileNotFoundError, HaulConfigError) as exc:
            app._log(f"[red]{escape(str(exc))}[/]")
            return
        app._log(f"[dim]Loaded haul config: [cyan]{escape(str(source))}[/][/]")
        dispatch_haul_loop(
            app,
            skip_delay=skip_delay,
            raw_command=raw_command or f"{'!' if skip_delay else ''}haul load {source}".strip(),
        )
        return
    if not station_1_buying:
        app._start_haul_prompt(
            commodity="",
            prompt_for_commodity=True,
            skip_delay=skip_delay,
            raw_command=raw_command,
        )
    else:
        app._start_haul_prompt(
            commodity=station_1_buying,
            prompt_for_commodity=False,
            skip_delay=skip_delay,
            raw_command=raw_command,
        )


def load_haul_from_trade_route(
    app: HaulHost,
    *,
    route_index: int,
    skip_delay: bool = False,
    raw_command: str | None = None,
) -> None:
    route = next((item for item in app._trade_routes.routes if item.index == route_index), None)
    if route is None:
        app._log(f"[red]No trade-route result #{route_index} is loaded.[/]")
        return
    load_haul_from_trade_route_entry(
        app,
        route=route,
        skip_delay=skip_delay,
        raw_command=raw_command,
    )


def load_haul_from_trade_route_entry(
    app: HaulHost,
    *,
    route: TradeRoute,
    skip_delay: bool = False,
    raw_command: str | None = None,
) -> None:
    if not route.source_buy_commodity:
        app._log(
            "[red]The selected route does not expose a source buy commodity, so it cannot prefill haul.[/]"
        )
        return

    app._log(
        f"Loading haul from route [cyan]{escape(route.from_station)}[/] -> "
        f"[cyan]{escape(route.to_station)}[/]"
    )
    app._start_haul_prompt(
        commodity="",
        prompt_for_commodity=True,
        seed={
            "station_1_buying": route.source_buy_commodity,
            "station_1": route.from_station,
            "station_1_system": route.from_system,
            "station_1_on_land": "false",
            "station_2_buying": route.target_buy_commodity or "",
            "station_2": route.to_station,
            "station_2_system": route.to_system,
            "station_2_on_land": "false",
        },
        skip_delay=skip_delay,
        raw_command=raw_command,
    )


def open_trade_route_picker(app: HaulHost) -> None:
    if not app._trade_routes.routes:
        return
    app._trade_route_picker_open = True
    if app._selected_trade_route_index not in {route.index for route in app._trade_routes.routes}:
        app._selected_trade_route_index = app._trade_routes.routes[0].index
    app._refresh_trade_routes()


def close_trade_route_picker(app: HaulHost) -> None:
    if not app._trade_route_picker_open:
        return
    app._trade_route_picker_open = False
    app._refresh_trade_routes()


def _set_trade_routes_loading(app: HaulHost, *, system_name: str, query_url: str) -> None:
    app._trade_routes = TradeRoutesData(
        system_name=system_name,
        query_url=query_url,
        searched_at=now_iso(),
        loading=True,
        error=None,
        routes=[],
    )
    app._trade_route_picker_open = False
    app._selected_trade_route_index = None
    app._presented_trade_route_query_url = query_url
    app._presented_trade_route_searched_at = app._trade_routes.searched_at
    app._refresh_trade_routes()
    app._publish_protocol_data_refresh()


def _set_trade_routes_loaded(app: HaulHost, result) -> None:
    debug_log = getattr(app, "_debug_log", None)
    if callable(debug_log):
        first_route = result.routes[0] if result.routes else None
        debug_log(
            "trade_routes_loaded",
            system_name=result.system_name,
            route_count=len(result.routes),
            first_route_index=first_route.index if first_route is not None else None,
            first_route_profit_per_trip=(
                first_route.profit_per_trip if first_route is not None else None
            ),
            first_route_profit_per_hour=(
                first_route.profit_per_hour if first_route is not None else None
            ),
            first_route_raw_text=(first_route.raw_text if first_route is not None else ""),
        )
    app._trade_routes = TradeRoutesData(
        system_name=result.system_name,
        query_url=result.query_url,
        searched_at=result.searched_at,
        loading=False,
        error=None,
        routes=list(result.routes),
    )
    app._selected_trade_route_index = app._trade_routes.routes[0].index if app._trade_routes.routes else None
    app._trade_route_picker_open = bool(app._trade_routes.routes)
    app._presented_trade_route_query_url = result.query_url
    app._presented_trade_route_searched_at = result.searched_at
    app._refresh_trade_routes()
    app._publish_protocol_data_refresh()


def _set_trade_routes_error(app: HaulHost, *, system_name: str, query_url: str, message: str) -> None:
    app._trade_routes = TradeRoutesData(
        system_name=system_name,
        query_url=query_url,
        searched_at=now_iso(),
        loading=False,
        error=message,
        routes=[],
    )
    app._trade_route_picker_open = False
    app._selected_trade_route_index = None
    app._presented_trade_route_query_url = query_url
    app._presented_trade_route_searched_at = app._trade_routes.searched_at
    app._refresh_trade_routes()
    app._publish_protocol_data_refresh()


def dispatch_haul_search(
    app: HaulHost,
    *,
    system_name: str,
    query_params: dict[str, str],
    skip_delay: bool = False,
    raw_command: str | None = None,
) -> None:
    query_url = build_trade_routes_url(system_name, query_params=query_params)
    history_params = {
        "mode": "search",
        "near_system": system_name,
        **{str(key): str(value) for key, value in query_params.items()},
    }
    app._record_history_entry(
        CommandHistoryEntry(
            raw=raw_command or f"{'!' if skip_delay else ''}haul search {system_name}".strip(),
            command="haul",
            params=history_params,
            timestamp=now_iso(),
        )
    )

    def on_start() -> None:
        app._log(f"Searching Inara trade routes for [cyan]{escape(system_name)}[/]...")
        _set_trade_routes_loading(app, system_name=system_name, query_url=query_url)

    def run_search() -> None:
        try:
            result = search_trade_routes(
                system_name,
                query_params=query_params,
                debug_hook=getattr(app, "_debug_log", None),
            )
        except Exception as exc:
            app.call_from_thread(
                _set_trade_routes_error,
                app,
                system_name=system_name,
                query_url=query_url,
                message=str(exc),
            )
            app.call_from_thread(
                app._log,
                f"[red]Failed to load Inara routes for {escape(system_name)}: {escape(str(exc))}[/]",
            )
            return None
        app.call_from_thread(_set_trade_routes_loaded, app, result)
        app.call_from_thread(
            app._log,
            f"[green]Loaded {len(result.routes)} Inara route(s) for [cyan]{escape(system_name)}[/].[/]",
        )
        return None

    app._start_delayed_routine(
        description=f"haul search {system_name}",
        start_message="",
        skip_delay=skip_delay,
        fn=run_search,
        active_routine_name="haul_search",
        on_start=on_start,
    )


def dispatch_haul_loop(
    app: HaulHost,
    *,
    skip_delay: bool = False,
    raw_command: str | None = None,
) -> None:
    station_1_buying = app._haul_params.get("station_1_buying", "")
    station_1 = app._haul_params.get("station_1", "")
    station_1_system = app._haul_params.get("station_1_system", "")
    station_1_on_land = _haul_param_as_bool(app._haul_params.get("station_1_on_land", ""))
    station_2_buying = app._haul_params.get("station_2_buying", "")
    station_2 = app._haul_params.get("station_2", "")
    station_2_system = app._haul_params.get("station_2_system", "")
    station_2_on_land = _haul_param_as_bool(app._haul_params.get("station_2_on_land", ""))
    galaxy_map_settle_raw = app._haul_params.get("galaxy_map_settle", "")
    dock_timeout_raw = app._haul_params.get("dock_timeout", "")

    if not station_1 and app._ship.station:
        station_1 = app._ship.station
        app._log(f"[dim]Station 1 defaulting to current station: [cyan]{escape(station_1)}[/][/]")
    if not station_1_system and app._ship.system:
        station_1_system = app._ship.system
        app._log(f"[dim]Station 1 system defaulting to current system: [cyan]{escape(station_1_system)}[/][/]")
    if (
        (not station_1_buying and not station_2_buying)
        or not station_1
        or not station_2
        or not station_2_system
    ):
        app._log(f"[red]{escape(error_text.render(app._config, 'haul_params_required'))}[/]")
        return

    progress = app._make_progress()
    controls = app._make_controls(progress)
    sleeper = app._make_sleeper()
    time_fn = app._time_fn
    galaxy_map_settle = (
        float(galaxy_map_settle_raw)
        if galaxy_map_settle_raw
        else app._config.controls.galaxy_map_settle_seconds
    )
    dock_timeout = (
        float(dock_timeout_raw)
        if dock_timeout_raw
        else app._config.controls.haul_dock_timeout_seconds
    )
    journal_dir = app._journal_dir
    watcher = app._make_watcher()
    runtime = _build_haul_runtime(
        app,
        controls=controls,
        watcher=watcher,
        sleeper=sleeper,
        time_fn=time_fn,
        progress_fn=progress,
        dock_timeout_s=dock_timeout,
        galaxy_map_settle_s=galaxy_map_settle,
    )
    route = TwoWayHaulRoute(
        station_1=StationLeg(
            index=1,
            station=station_1,
            system=station_1_system,
            on_land=station_1_on_land,
            buy_commodity=station_1_buying,
            sell_commodity=station_2_buying,
        ),
        station_2=StationLeg(
            index=2,
            station=station_2,
            system=station_2_system,
            on_land=station_2_on_land,
            buy_commodity=station_2_buying,
            sell_commodity=station_1_buying,
        ),
    )
    app._clear_pending_haul_stop()

    app._record_history_entry(CommandHistoryEntry(
        raw=raw_command or f"{'!' if skip_delay else ''}haul {station_1_buying}",
        command="haul",
        params={
            "station_1_buying": station_1_buying,
            "station_1": station_1,
            "station_1_system": station_1_system,
            "station_1_on_land": "true" if station_1_on_land else "false",
            "station_2_buying": station_2_buying,
            "station_2": station_2,
            "station_2_system": station_2_system,
            "station_2_on_land": "true" if station_2_on_land else "false",
            "galaxy_map_settle": str(galaxy_map_settle),
            "dock_timeout": str(dock_timeout),
        },
        timestamp=now_iso(),
    ))

    label_parts = [
        (
            f"station 1 [cyan]{escape(station_1)}[/]: buy [cyan]{escape(station_1_buying)}[/]"
            if station_1_buying
            else f"station 1 [cyan]{escape(station_1)}[/]: [dim]no buy[/]"
        ),
        (
            f"station 2 [cyan]{escape(station_2)}[/]: buy [cyan]{escape(station_2_buying)}[/]"
            if station_2_buying
            else f"station 2 [cyan]{escape(station_2)}[/]: [dim]no buy[/]"
        ),
    ]
    if station_1_system:
        label_parts.append(f"station 1 sys: [cyan]{escape(station_1_system)}[/]")
    if station_1_on_land:
        label_parts.append("station 1 landing: [cyan]on land[/]")
    if station_2_system:
        label_parts.append(f"station 2 sys: [cyan]{escape(station_2_system)}[/]")
    if station_2_on_land:
        label_parts.append("station 2 landing: [cyan]on land[/]")
    label_parts.append(f"map settle: [cyan]{galaxy_map_settle:.1f}s[/]")
    label_parts.append(f"dock timeout: [cyan]{dock_timeout:.1f}s[/]")

    def on_start() -> None:
        app._log(f"Starting haul loop: {', '.join(label_parts)} (infinite)...")
        app._start_haul_stats(
            station_1_buying=station_1_buying,
            station_2_buying=station_2_buying,
            station_1=station_1,
            station_2=station_2,
        )

    app._start_delayed_routine(
        description=f"haul {station_1_buying}",
        start_message="",
        skip_delay=skip_delay,
        fn=lambda: haul_loop_two_way(
            runtime,
            route=route,
            stop_requested_fn=lambda: app._haul_stop_requested,
        ),
        active_routine_name="haul",
        on_start=on_start,
    )


def cmd_multi_leg_haul(
    app: HaulHost,
    rest: str,
    *,
    skip_delay: bool = False,
    raw_command: str | None = None,
) -> None:
    if not app._check_routine_ready():
        return
    source = rest.strip()
    if not source:
        app._log("[red]Usage: multi_leg_haul <route.json | spansh-url>[/]")
        return
    dispatch_multi_leg_haul(
        app,
        source=source,
        skip_delay=skip_delay,
        raw_command=raw_command,
    )


def dispatch_multi_leg_haul(
    app: HaulHost,
    *,
    source: str,
    skip_delay: bool = False,
    raw_command: str | None = None,
) -> None:
    try:
        definition = load_multi_leg_haul_definition(source)
    except Exception as exc:
        app._log(f"[red]Failed to load multi-leg haul source: {escape(str(exc))}[/]")
        return

    progress = app._make_progress()
    controls = app._make_controls(progress)
    sleeper = app._make_sleeper()
    time_fn = app._time_fn
    watcher = app._make_watcher()
    runtime = _build_haul_runtime(
        app,
        controls=controls,
        watcher=watcher,
        sleeper=sleeper,
        time_fn=time_fn,
        progress_fn=progress,
        dock_timeout_s=app._config.controls.haul_dock_timeout_seconds,
        galaxy_map_settle_s=app._config.controls.galaxy_map_settle_seconds,
        request_timeout_s=20.0,
    )
    app._clear_pending_haul_stop()
    app._record_history_entry(CommandHistoryEntry(
        raw=raw_command or f"{'!' if skip_delay else ''}multi_leg_haul {source}",
        command="multi_leg_haul",
        params={"source": source},
        timestamp=now_iso(),
    ))

    route_label = f"{definition.route_name} ({definition.total_legs} legs)"
    route_source = definition.source_provider or "json"

    def on_start() -> None:
        app._stop_haul_stats()
        app._log(
            "Starting multi-leg haul: "
            f"[cyan]{escape(route_label)}[/] from [cyan]{escape(route_source)}[/]"
        )

    app._start_delayed_routine(
        description=f"multi_leg_haul {source}",
        start_message="",
        skip_delay=skip_delay,
        fn=lambda: multi_leg_haul(
            runtime,
            definition=definition,
            stop_requested_fn=lambda: app._haul_stop_requested,
        ),
        active_routine_name="multi_leg_haul",
        on_start=on_start,
    )
