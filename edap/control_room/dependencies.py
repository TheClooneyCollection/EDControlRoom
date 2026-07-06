from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

from edap.control_room.models import HaulStats, MarketData, ShipState
from edap.control_room.routine_stop import RoutineStopMode
from edap.control_room_state import CommandHistoryEntry
from edap.haul_search_config import HaulSearchConfigError, load_haul_search_config
from edap.inara.trade_routes import TradeRoute, trade_route_search_defaults

if TYPE_CHECKING:
    from edap.control_room.app import ControlRoomApp


@dataclass(frozen=True)
class ActivityLogItem:
    entry_id: str
    timestamp: str
    message_text: str
    severity: str = "info"


@dataclass(frozen=True)
class ActivityLogReadModel:
    entries: tuple[ActivityLogItem, ...]


@dataclass(frozen=True)
class CommandHistoryReadModel:
    default_haul: dict[str, str]
    history_entries: tuple[CommandHistoryEntry, ...]
    history_limit: int


@dataclass(frozen=True)
class RoutineReadModel:
    routine_active: bool
    active_routine_name: str | None
    haul_stop_requested: bool
    haul_pause_requested: bool
    haul_paused: bool
    verbose_controls: bool
    instant_mode: bool
    shutdown_requested: bool
    shutdown_finalized: bool
    haul_phase: str | None = None
    haul_phase_station_index: int | None = None


@dataclass(frozen=True)
class SessionReadModel:
    session_id: str
    client_role: str
    client_name: str
    active_operator_name: str | None = None


@dataclass(frozen=True)
class ServerStatusReadModel:
    server_name: str
    server_version: str
    runtime_platform: str
    journal_source_status: str
    bindings_source_status: str
    bindings_loaded: bool
    capability_names: tuple[str, ...] = ()
    operator_mode: str = "embedded_local"
    input_target_summary: str = "foreground window"
    web_form_defaults: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ControlRoomDataReadModel:
    ship: ShipState
    market: MarketData
    haul_session: HaulStats
    command_history: CommandHistoryReadModel
    activity_log: ActivityLogReadModel
    routine: RoutineReadModel
    session: SessionReadModel
    server_status: ServerStatusReadModel
    home_system: str = ""
    selected_trade_route: TradeRoute | None = None
    running_trade_route: TradeRoute | None = None


class ControlRoomDataSource(Protocol):
    def current(self) -> ControlRoomDataReadModel: ...


class ControlRoomExecution(Protocol):
    def submit_command(self, raw: str, *, skip_delay: bool | None = None) -> None: ...

    def dispatch_destination(
        self,
        destination: str,
        galaxy_map_settle: float,
        *,
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None: ...

    def dispatch_haul_loop(
        self,
        *,
        params: dict[str, str] | None = None,
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None: ...

    def load_trade_route(
        self,
        route: TradeRoute,
        *,
        raw_command: str | None = None,
    ) -> None: ...

    def handle_haul_prompt(self, value: str) -> None: ...

    def handle_haul_confirm_prompt(self, value: str) -> None: ...

    def cancel_active_routine(self, *, stop_mode: RoutineStopMode = "toggle") -> None: ...


@dataclass(frozen=True)
class ControlRoomDependencies:
    data_source: ControlRoomDataSource
    execution: ControlRoomExecution


class LocalControlRoomDataSource:
    def __init__(self, app: ControlRoomApp) -> None:
        self._app = app

    def current(self) -> ControlRoomDataReadModel:
        app = self._app
        time_fn = getattr(app, "_time_fn", None)
        now = time_fn() if callable(time_fn) else None
        return ControlRoomDataReadModel(
            ship=_copy_ship_state(app._ship),
            market=_copy_market_data(app._market),
            haul_session=_copy_haul_stats(app._haul_stats, now=now),
            command_history=CommandHistoryReadModel(
                default_haul=dict(app._saved_state.default_haul),
                history_entries=tuple(app._saved_state.history),
                history_limit=app._config.control_room.history_limit,
            ),
            activity_log=ActivityLogReadModel(
                entries=tuple(
                    ActivityLogItem(
                        entry_id=str(entry.entry_id),
                        timestamp=str(entry.timestamp),
                        message_text=str(entry.message_text),
                        severity=str(getattr(entry, "severity", "info")),
                    )
                    for entry in app._protocol_activity_log
                )
            ),
            routine=RoutineReadModel(
                routine_active=app._runtime_state.routine_active,
                active_routine_name=app._runtime_state.active_routine_name,
                haul_stop_requested=app._runtime_state.haul_stop_requested,
                haul_pause_requested=app._runtime_state.haul_pause_requested,
                haul_paused=app._runtime_state.haul_paused,
                verbose_controls=app._runtime_state.verbose_controls,
                instant_mode=app._runtime_state.instant_mode,
                shutdown_requested=app._runtime_state.shutdown_requested,
                shutdown_finalized=app._runtime_state.shutdown_finalized,
                haul_phase=(
                    app._runtime_state.haul_phase
                    if app._runtime_state.routine_active
                    and app._runtime_state.active_routine_name == "haul"
                    else None
                ),
                haul_phase_station_index=(
                    app._runtime_state.haul_phase_station_index
                    if app._runtime_state.routine_active
                    and app._runtime_state.active_routine_name == "haul"
                    else None
                ),
            ),
            session=SessionReadModel(
                session_id="local-session",
                client_role="active_operator",
                client_name="local-control-room",
                active_operator_name="local-control-room",
            ),
            server_status=ServerStatusReadModel(
                server_name="ED Control Room",
                server_version=app._current_version,
                runtime_platform=app._config.runtime.platform,
                journal_source_status=app._ctx.journal.cli_source_status(),
                bindings_source_status=app._ctx.bindings.cli_source_status(),
                bindings_loaded=app._ctx.binding_lookup is not None,
                input_target_summary=_input_target_summary(app),
                web_form_defaults=_web_form_defaults(app),
            ),
            home_system=app._config.control_room.home_system,
            selected_trade_route=_selected_trade_route(app) or app._saved_state.selected_trade_route,
            running_trade_route=app._saved_state.running_trade_route,
        )


def _input_target_summary(app: ControlRoomApp) -> str:
    describe_input_target = getattr(app, "_describe_input_target", None)
    if callable(describe_input_target):
        return str(describe_input_target())
    return "foreground window"


def _web_form_defaults(app: ControlRoomApp) -> dict[str, str]:
    search_defaults = trade_route_search_defaults()
    try:
        search_defaults.update(load_haul_search_config())
    except FileNotFoundError:
        pass
    except HaulSearchConfigError:
        search_defaults = trade_route_search_defaults()

    if app._ship.cargo_capacity:
        search_defaults["cargo_capacity"] = str(app._ship.cargo_capacity)

    min_landing_pad = search_defaults.get("min_landing_pad", "").strip().lower()
    use_surface_stations = search_defaults.get("use_surface_stations", "").strip().lower()
    order_by = search_defaults.get("order_by", "").strip()
    controls = getattr(getattr(app, "_config", None), "controls", None)
    return {
        "startingCapital": str(app._ship.credits or ""),
        "cargoCapacity": search_defaults.get("cargo_capacity", ""),
        "maxRouteDistanceLy": search_defaults.get("max_route_distance_ly", ""),
        "maxStationDistanceLs": search_defaults.get("max_station_distance_ls", ""),
        "maxMarketAge": "",
        "requiresLargePad": "true" if min_landing_pad == "large" else "false",
        "allowPlanetary": "true" if use_surface_stations in {"yes", "true", "1"} else "false",
        "metric": "Profit / trip" if order_by == "best_profit" else "Profit / hour",
        "galaxyMapSettle": _format_web_number(getattr(controls, "galaxy_map_settle_seconds", "")),
        "dockTimeout": _format_web_number(getattr(controls, "haul_dock_timeout_seconds", "")),
    }


def _format_web_number(value: object) -> str:
    if value == "":
        return ""
    return str(value)


class LocalControlRoomExecution:
    def __init__(self, app: ControlRoomApp) -> None:
        self._app = app

    def submit_command(self, raw: str, *, skip_delay: bool | None = None) -> None:
        self._app._facade.dispatch_command(raw, skip_delay=skip_delay)

    def dispatch_destination(
        self,
        destination: str,
        galaxy_map_settle: float,
        *,
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None:
        self._app._facade.dispatch_dest(
            destination,
            galaxy_map_settle,
            skip_delay=skip_delay,
            raw_command=raw_command,
        )

    def dispatch_haul_loop(
        self,
        *,
        params: dict[str, str] | None = None,
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None:
        if params is not None:
            self._app._haul_params = {str(key): str(value) for key, value in params.items()}
        self._app._facade.dispatch_haul_loop(
            skip_delay=skip_delay,
            raw_command=raw_command,
        )

    def load_trade_route(
        self,
        route: TradeRoute,
        *,
        raw_command: str | None = None,
    ) -> None:
        self._app._facade.load_trade_route(route, raw_command=raw_command)

    def handle_haul_prompt(self, value: str) -> None:
        self._app._facade.handle_haul_prompt(value)

    def handle_haul_confirm_prompt(self, value: str) -> None:
        self._app._facade.handle_haul_confirm_prompt(value)

    def cancel_active_routine(self, *, stop_mode: RoutineStopMode = "toggle") -> None:
        if stop_mode == "toggle":
            self._app._handle_interrupt("Ctrl-C")
            return
        self._app._handle_routine_stop_request("Ctrl-C", stop_mode=stop_mode)


def build_local_control_room_dependencies(app: ControlRoomApp) -> ControlRoomDependencies:
    return ControlRoomDependencies(
        data_source=LocalControlRoomDataSource(app),
        execution=LocalControlRoomExecution(app),
    )


def _copy_ship_state(ship: ShipState) -> ShipState:
    return ShipState(
        commander=ship.commander,
        ship_type=ship.ship_type,
        system=ship.system,
        station=ship.station,
        status=ship.status,
        fuel_level=ship.fuel_level,
        fuel_capacity=ship.fuel_capacity,
        credits=ship.credits,
        cargo_count=ship.cargo_count,
        cargo_capacity=ship.cargo_capacity,
        max_jump_range_ly=ship.max_jump_range_ly,
        cargo_inventory=list(ship.cargo_inventory),
        target=ship.target,
        destination_system=ship.destination_system,
        destination_body=ship.destination_body,
        destination_name=ship.destination_name,
    )


def _copy_market_data(market: MarketData) -> MarketData:
    return MarketData(
        station=market.station,
        system=market.system,
        timestamp=market.timestamp,
        market_id=market.market_id,
        items=list(market.items),
        locked=market.locked,
    )


def _copy_haul_stats(haul: HaulStats, *, now: float | None = None) -> HaulStats:
    session_started_at = haul.session_started_at
    session_elapsed_s = haul.session_elapsed_s
    if now is not None and session_started_at is not None:
        session_elapsed_s = max(0.0, now - session_started_at)
        session_started_at = None

    current_run_started_at = haul.current_run_started_at
    current_run_elapsed_s = haul.current_run_elapsed_s
    if now is not None:
        if current_run_started_at is not None and not haul.docked_back_at_station_1:
            current_run_elapsed_s = max(0.0, now - current_run_started_at)
        current_run_started_at = None

    return HaulStats(
        station_1_buying=haul.station_1_buying,
        station_2_buying=haul.station_2_buying,
        station_1=haul.station_1,
        station_2=haul.station_2,
        session_started_at=session_started_at,
        session_elapsed_s=session_elapsed_s,
        session_active=haul.session_active,
        active=haul.active,
        clean_run_active=haul.clean_run_active,
        waiting_for_station_1_departure=haul.waiting_for_station_1_departure,
        resumed_mid_run=haul.resumed_mid_run,
        docked_back_at_station_1=haul.docked_back_at_station_1,
        current_run_started_at=current_run_started_at,
        current_run_elapsed_s=current_run_elapsed_s,
        current_run_profit=haul.current_run_profit,
        expected_profit_per_trip=haul.expected_profit_per_trip,
        expected_profit_per_trip_text=haul.expected_profit_per_trip_text,
        completed_runs=haul.completed_runs,
        accumulated_profit=haul.accumulated_profit,
        cargo_moved_t=haul.cargo_moved_t,
        last_run_profit=haul.last_run_profit,
        last_run_profit_delta=haul.last_run_profit_delta,
        last_run_elapsed_s=haul.last_run_elapsed_s,
        total_run_elapsed_s=haul.total_run_elapsed_s,
        paused=haul.paused,
    )


def _selected_trade_route(app: ControlRoomApp) -> TradeRoute | None:
    picker_state = getattr(app, "_trade_route_picker_state", None)
    trade_routes = getattr(app, "_trade_routes", None)
    selected_index = getattr(picker_state, "selected_route_index", None)
    if selected_index is None:
        return None
    routes = getattr(trade_routes, "routes", ())
    return next(
        (route for route in routes if route.index == selected_index),
        None,
    )
