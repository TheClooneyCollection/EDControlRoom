from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from edap.control_room.models import HaulStats, MarketData, ShipState
from edap.control_room_state import CommandHistoryEntry
from edap.inara.trade_routes import TradeRoute

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
    verbose_controls: bool
    instant_mode: bool
    shutdown_requested: bool
    shutdown_finalized: bool


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

    def cancel_active_routine(self) -> None: ...


@dataclass(frozen=True)
class ControlRoomDependencies:
    data_source: ControlRoomDataSource
    execution: ControlRoomExecution


class LocalControlRoomDataSource:
    def __init__(self, app: ControlRoomApp) -> None:
        self._app = app

    def current(self) -> ControlRoomDataReadModel:
        app = self._app
        return ControlRoomDataReadModel(
            ship=_copy_ship_state(app._ship),
            market=_copy_market_data(app._market),
            haul_session=_copy_haul_stats(app._haul_stats),
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
                verbose_controls=app._runtime_state.verbose_controls,
                instant_mode=app._runtime_state.instant_mode,
                shutdown_requested=app._runtime_state.shutdown_requested,
                shutdown_finalized=app._runtime_state.shutdown_finalized,
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
            ),
        )


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

    def cancel_active_routine(self) -> None:
        self._app._handle_interrupt("Ctrl-C")


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
        items=list(market.items),
        locked=market.locked,
    )


def _copy_haul_stats(haul: HaulStats) -> HaulStats:
    return HaulStats(
        station_1_buying=haul.station_1_buying,
        station_2_buying=haul.station_2_buying,
        station_1=haul.station_1,
        station_2=haul.station_2,
        session_started_at=haul.session_started_at,
        session_elapsed_s=haul.session_elapsed_s,
        session_active=haul.session_active,
        active=haul.active,
        clean_run_active=haul.clean_run_active,
        waiting_for_station_1_departure=haul.waiting_for_station_1_departure,
        resumed_mid_run=haul.resumed_mid_run,
        docked_back_at_station_1=haul.docked_back_at_station_1,
        current_run_started_at=haul.current_run_started_at,
        current_run_elapsed_s=haul.current_run_elapsed_s,
        current_run_profit=haul.current_run_profit,
        completed_runs=haul.completed_runs,
        accumulated_profit=haul.accumulated_profit,
        last_run_profit=haul.last_run_profit,
        last_run_elapsed_s=haul.last_run_elapsed_s,
        total_run_elapsed_s=haul.total_run_elapsed_s,
    )
