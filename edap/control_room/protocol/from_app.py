from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable, Protocol

from edap.control_room_state import CommandHistoryEntry

from .snapshot import (
    ActiveOperatorSnapshot,
    ActivityLogEntry,
    ClientRole,
    CommandHistoryEntrySnapshot,
    CommandHistorySnapshot,
    ConnectedClientSnapshot,
    ControlRoomSnapshot,
    HaulSessionSnapshot,
    MarketSnapshot,
    ServerStatusSnapshot,
    SessionSnapshot,
    ShipSnapshot,
    TradeRouteSnapshot,
    TradeRoutesSnapshot,
    UiStateSnapshot,
)

if TYPE_CHECKING:
    from edap.control_room.app import ControlRoomApp


_DEFAULT_SERVER_NAME = "ED Control Room"


class SnapshotHost(Protocol):
    _ship: Any
    _market: Any
    _haul_stats: Any
    _runtime_state: Any
    _saved_state: Any
    _trade_routes: Any
    _protocol_activity_log: list[ActivityLogEntry]
    _config: Any
    _ctx: Any
    _current_version: str

    def _activity_auto_follow_paused(self) -> bool: ...
    def query_one(self, selector: str, widget_type: object | None = None) -> object: ...


def snapshot_from_app(
    app: SnapshotHost | ControlRoomApp,
    *,
    session_id: str = "local-session",
    client_role: ClientRole = "active_operator",
    client_name: str = "local-control-room",
    connected_clients: Iterable[ConnectedClientSnapshot] | None = None,
    active_operator: ActiveOperatorSnapshot | None = None,
    activity_log: Iterable[ActivityLogEntry] | None = None,
    capability_names: Iterable[str] = (),
    operator_mode: str = "embedded_local",
) -> ControlRoomSnapshot:
    connected = list(connected_clients or [])
    if not connected:
        connected = [
            ConnectedClientSnapshot(
                session_id=session_id,
                client_name=client_name,
                client_role=client_role,
            )
        ]

    resolved_active_operator = active_operator
    if resolved_active_operator is None and client_role == "active_operator":
        resolved_active_operator = ActiveOperatorSnapshot(
            session_id=session_id,
            client_name=client_name,
        )

    return ControlRoomSnapshot(
        session=SessionSnapshot(session_id=session_id, client_role=client_role),
        connected_clients=connected,
        active_operator=resolved_active_operator,
        ship=_ship_snapshot(app),
        market=_market_snapshot(app),
        haul_session=_haul_session_snapshot(app),
        ui_state=_ui_state_snapshot(app),
        command_history=_command_history_snapshot(app),
        activity_log=list(app._protocol_activity_log if activity_log is None else activity_log),
        server_status=_server_status_snapshot(
            app,
            capability_names=list(capability_names),
            operator_mode=operator_mode,
        ),
        trade_routes=_trade_routes_snapshot(app),
    )


def _ship_snapshot(app: SnapshotHost) -> ShipSnapshot:
    ship = app._ship
    return ShipSnapshot(
        commander_name=ship.commander,
        ship_type=ship.ship_type,
        system_name=ship.system,
        station_name=ship.station,
        status=ship.status,
        fuel_level=ship.fuel_level,
        fuel_capacity=ship.fuel_capacity,
        credits=ship.credits,
        cargo_count=ship.cargo_count,
        cargo_capacity=ship.cargo_capacity,
        cargo_inventory=list(ship.cargo_inventory),
        target_name=ship.target,
        destination_system=ship.destination_system,
        destination_body=ship.destination_body,
        destination_name=ship.destination_name,
    )


def _market_snapshot(app: SnapshotHost) -> MarketSnapshot:
    market = app._market
    return MarketSnapshot(
        station_name=market.station,
        system_name=market.system,
        market_timestamp=market.timestamp,
        items=list(market.items),
    )


def _haul_session_snapshot(app: SnapshotHost) -> HaulSessionSnapshot:
    stats = app._haul_stats
    return HaulSessionSnapshot(
        station_1_buying=stats.station_1_buying,
        station_2_buying=stats.station_2_buying,
        station_1=stats.station_1,
        station_2=stats.station_2,
        session_started_at=stats.session_started_at,
        session_elapsed_seconds=stats.session_elapsed_s,
        session_active=stats.session_active,
        active=stats.active,
        clean_run_active=stats.clean_run_active,
        waiting_for_station_1_departure=stats.waiting_for_station_1_departure,
        resumed_mid_run=stats.resumed_mid_run,
        docked_back_at_station_1=stats.docked_back_at_station_1,
        current_run_started_at=stats.current_run_started_at,
        current_run_elapsed_seconds=stats.current_run_elapsed_s,
        current_run_profit=stats.current_run_profit,
        completed_runs=stats.completed_runs,
        accumulated_profit=stats.accumulated_profit,
        last_run_profit=stats.last_run_profit,
        last_run_elapsed_seconds=stats.last_run_elapsed_s,
        total_run_elapsed_seconds=stats.total_run_elapsed_s,
    )


def _ui_state_snapshot(app: SnapshotHost) -> UiStateSnapshot:
    state = app._runtime_state
    return UiStateSnapshot(
        routine_active=state.routine_active,
        active_routine_name=state.active_routine_name,
        haul_stop_requested=state.haul_stop_requested,
        verbose_controls=state.verbose_controls,
        instant_mode=state.instant_mode,
        activity_auto_follow_paused=app._activity_auto_follow_paused(),
        shutdown_requested=state.shutdown_requested,
        shutdown_finalized=state.shutdown_finalized,
    )


def _command_history_snapshot(app: SnapshotHost) -> CommandHistorySnapshot:
    return CommandHistorySnapshot(
        default_haul=dict(app._saved_state.default_haul),
        history_entries=[
            _command_history_entry_snapshot(entry)
            for entry in app._saved_state.history
        ],
        history_limit=app._config.control_room.history_limit,
    )


def _server_status_snapshot(
    app: SnapshotHost,
    *,
    capability_names: list[str],
    operator_mode: str,
) -> ServerStatusSnapshot:
    return ServerStatusSnapshot(
        server_name=_DEFAULT_SERVER_NAME,
        server_version=app._current_version,
        runtime_platform=app._config.runtime.platform,
        journal_source_status=app._ctx.journal.cli_source_status(),
        bindings_source_status=app._ctx.bindings.cli_source_status(),
        bindings_loaded=app._ctx.binding_lookup is not None,
        capability_names=capability_names,
        operator_mode=operator_mode,
    )


def _trade_routes_snapshot(app: SnapshotHost) -> TradeRoutesSnapshot:
    trade_routes = app._trade_routes
    return TradeRoutesSnapshot(
        system_name=trade_routes.system_name,
        query_url=trade_routes.query_url,
        searched_at=trade_routes.searched_at,
        loading=trade_routes.loading,
        error=trade_routes.error,
        routes=[
            TradeRouteSnapshot(
                index=route.index,
                from_station=route.from_station,
                from_system=route.from_system,
                to_station=route.to_station,
                to_system=route.to_system,
                source_buy_commodity=route.source_buy_commodity,
                target_buy_commodity=route.target_buy_commodity,
                from_station_distance=route.from_station_distance,
                to_station_distance=route.to_station_distance,
                distance_from_system=route.distance_from_system,
                route_distance=route.route_distance,
                profit_per_unit=route.profit_per_unit,
                profit_per_trip=route.profit_per_trip,
                profit_per_hour=route.profit_per_hour,
                updated=route.updated,
                raw_text=route.raw_text,
                url_links=list(route.url_links),
            )
            for route in trade_routes.routes
        ],
    )


def _command_history_entry_snapshot(entry: CommandHistoryEntry) -> CommandHistoryEntrySnapshot:
    return CommandHistoryEntrySnapshot(
        raw_command=entry.raw,
        command_name=entry.command,
        arguments=dict(entry.params),
        timestamp=entry.timestamp,
    )
