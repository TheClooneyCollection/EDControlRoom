from __future__ import annotations

from .events import ActivityLogAppendedEvent, AnnouncementEvent, SnapshotUpdatedEvent
from .snapshot import (
    ActivityLogEntry,
    ActiveOperatorSnapshot,
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


def snapshot_from_message(payload: dict[str, object]) -> ControlRoomSnapshot:
    session_payload = _mapping(payload["session"])
    active_operator_payload = payload.get("active_operator")
    return ControlRoomSnapshot(
        session=SessionSnapshot(
            session_id=str(session_payload["session_id"]),
            client_role=str(session_payload["client_role"]),
        ),
        connected_clients=[
            ConnectedClientSnapshot(
                session_id=str(client["session_id"]),
                client_name=str(client["client_name"]),
                client_role=str(client["client_role"]),
            )
            for client in (_mapping(item) for item in _sequence(payload["connected_clients"]))
        ],
        active_operator=(
            ActiveOperatorSnapshot(
                session_id=str(_mapping(active_operator_payload)["session_id"]),
                client_name=str(_mapping(active_operator_payload)["client_name"]),
            )
            if active_operator_payload is not None
            else None
        ),
        ship=_ship_snapshot(_mapping(payload["ship"])),
        market=_market_snapshot(_mapping(payload["market"])),
        haul_session=_haul_session_snapshot(_mapping(payload["haul_session"])),
        ui_state=_ui_state_snapshot(_mapping(payload["ui_state"])),
        command_history=_command_history_snapshot(_mapping(payload["command_history"])),
        activity_log=[
            _activity_log_entry(_mapping(entry))
            for entry in _sequence(payload["activity_log"])
        ],
        server_status=_server_status_snapshot(_mapping(payload["server_status"])),
        trade_routes=_trade_routes_snapshot(_mapping(payload.get("trade_routes", {}))),
    )


def event_from_message(message: dict[str, object]) -> ActivityLogAppendedEvent | AnnouncementEvent | SnapshotUpdatedEvent | None:
    message_type = str(message.get("message_type", ""))
    payload = _mapping(message.get("payload", {}))
    if message_type == "state.snapshot":
        return SnapshotUpdatedEvent(snapshot=snapshot_from_message(payload))
    if message_type == "event.activity_log_appended":
        return ActivityLogAppendedEvent(entry=_activity_log_entry(_mapping(payload["entry"])))
    if message_type == "event.announcement_emitted":
        raw_values = payload.get("message_values", {})
        values_mapping = _mapping(raw_values) if isinstance(raw_values, dict) else {}
        return AnnouncementEvent(
            announcement_id=str(payload["announcement_id"]),
            message_text=str(payload["message_text"]),
            message_values={str(key): value for key, value in values_mapping.items()},
        )
    return None


def _ship_snapshot(payload: dict[str, object]) -> ShipSnapshot:
    return ShipSnapshot(
        commander_name=_optional_str(payload.get("commander_name")),
        ship_type=_optional_str(payload.get("ship_type")),
        system_name=_optional_str(payload.get("system_name")),
        station_name=_optional_str(payload.get("station_name")),
        status=_optional_str(payload.get("status")),
        fuel_level=_optional_float(payload.get("fuel_level")),
        fuel_capacity=_optional_float(payload.get("fuel_capacity")),
        credits=_optional_int(payload.get("credits")),
        cargo_count=int(payload.get("cargo_count", 0)),
        cargo_capacity=_optional_int(payload.get("cargo_capacity")),
        cargo_inventory=[dict(_mapping(item)) for item in _sequence(payload.get("cargo_inventory", []))],
        target_name=_optional_str(payload.get("target_name")),
        destination_system=_optional_str(payload.get("destination_system")),
        destination_body=_optional_str(payload.get("destination_body")),
        destination_name=_optional_str(payload.get("destination_name")),
    )


def _market_snapshot(payload: dict[str, object]) -> MarketSnapshot:
    return MarketSnapshot(
        station_name=str(payload.get("station_name", "")),
        system_name=str(payload.get("system_name", "")),
        market_timestamp=str(payload.get("market_timestamp", "")),
        items=[dict(_mapping(item)) for item in _sequence(payload.get("items", []))],
    )


def _haul_session_snapshot(payload: dict[str, object]) -> HaulSessionSnapshot:
    return HaulSessionSnapshot(
        station_1_buying=str(payload.get("station_1_buying", "")),
        station_2_buying=str(payload.get("station_2_buying", "")),
        station_1=str(payload.get("station_1", "")),
        station_2=str(payload.get("station_2", "")),
        session_started_at=_optional_float(payload.get("session_started_at")),
        session_elapsed_seconds=float(payload.get("session_elapsed_seconds", 0.0)),
        session_active=bool(payload.get("session_active", False)),
        active=bool(payload.get("active", False)),
        clean_run_active=bool(payload.get("clean_run_active", False)),
        waiting_for_station_1_departure=bool(payload.get("waiting_for_station_1_departure", False)),
        resumed_mid_run=bool(payload.get("resumed_mid_run", False)),
        docked_back_at_station_1=bool(payload.get("docked_back_at_station_1", False)),
        current_run_started_at=_optional_float(payload.get("current_run_started_at")),
        current_run_elapsed_seconds=_optional_float(payload.get("current_run_elapsed_seconds")),
        current_run_profit=int(payload.get("current_run_profit", 0)),
        completed_runs=int(payload.get("completed_runs", 0)),
        accumulated_profit=int(payload.get("accumulated_profit", 0)),
        last_run_profit=_optional_int(payload.get("last_run_profit")),
        last_run_elapsed_seconds=_optional_float(payload.get("last_run_elapsed_seconds")),
        total_run_elapsed_seconds=float(payload.get("total_run_elapsed_seconds", 0.0)),
    )


def _ui_state_snapshot(payload: dict[str, object]) -> UiStateSnapshot:
    return UiStateSnapshot(
        routine_active=bool(payload.get("routine_active", False)),
        active_routine_name=_optional_str(payload.get("active_routine_name")),
        haul_stop_requested=bool(payload.get("haul_stop_requested", False)),
        verbose_controls=bool(payload.get("verbose_controls", False)),
        instant_mode=bool(payload.get("instant_mode", False)),
        activity_auto_follow_paused=bool(payload.get("activity_auto_follow_paused", False)),
        shutdown_requested=bool(payload.get("shutdown_requested", False)),
        shutdown_finalized=bool(payload.get("shutdown_finalized", False)),
    )


def _command_history_snapshot(payload: dict[str, object]) -> CommandHistorySnapshot:
    raw_default_haul = payload.get("default_haul", {})
    default_haul_mapping = _mapping(raw_default_haul) if isinstance(raw_default_haul, dict) else {}
    return CommandHistorySnapshot(
        default_haul={str(key): str(value) for key, value in default_haul_mapping.items()},
        history_entries=[
            _command_history_entry_snapshot(_mapping(entry))
            for entry in _sequence(payload.get("history_entries", []))
        ],
        history_limit=int(payload.get("history_limit", 1)),
    )


def _server_status_snapshot(payload: dict[str, object]) -> ServerStatusSnapshot:
    return ServerStatusSnapshot(
        server_name=str(payload.get("server_name", "")),
        server_version=str(payload.get("server_version", "")),
        runtime_platform=str(payload.get("runtime_platform", "")),
        journal_source_status=str(payload.get("journal_source_status", "")),
        bindings_source_status=str(payload.get("bindings_source_status", "")),
        bindings_loaded=bool(payload.get("bindings_loaded", False)),
        capability_names=[str(name) for name in _sequence(payload.get("capability_names", []))],
        operator_mode=_optional_str(payload.get("operator_mode")),
    )


def _trade_routes_snapshot(payload: dict[str, object]) -> TradeRoutesSnapshot:
    return TradeRoutesSnapshot(
        system_name=str(payload.get("system_name", "")),
        query_url=str(payload.get("query_url", "")),
        searched_at=str(payload.get("searched_at", "")),
        loading=bool(payload.get("loading", False)),
        error=_optional_str(payload.get("error")),
        routes=[
            TradeRouteSnapshot(
                index=int(entry.get("index", 0)),
                from_station=str(entry.get("from_station", "")),
                from_system=str(entry.get("from_system", "")),
                to_station=str(entry.get("to_station", "")),
                to_system=str(entry.get("to_system", "")),
                source_buy_commodity=_optional_str(entry.get("source_buy_commodity")),
                target_buy_commodity=_optional_str(entry.get("target_buy_commodity")),
                from_station_distance=_optional_str(entry.get("from_station_distance")),
                to_station_distance=_optional_str(entry.get("to_station_distance")),
                distance_from_system=_optional_str(entry.get("distance_from_system")),
                route_distance=_optional_str(entry.get("route_distance")),
                profit_per_unit=_optional_str(entry.get("profit_per_unit")),
                profit_per_trip=_optional_str(entry.get("profit_per_trip")),
                profit_per_hour=_optional_str(entry.get("profit_per_hour")),
                updated=_optional_str(entry.get("updated")),
                raw_text=str(entry.get("raw_text", "")),
                url_links=[str(link) for link in _sequence(entry.get("url_links", []))],
            )
            for entry in (_mapping(item) for item in _sequence(payload.get("routes", [])))
        ],
    )


def _activity_log_entry(payload: dict[str, object]) -> ActivityLogEntry:
    return ActivityLogEntry(
        entry_id=str(payload.get("entry_id", "")),
        timestamp=str(payload.get("timestamp", "")),
        message_text=str(payload.get("message_text", "")),
        severity=_optional_str(payload.get("severity")),
    )


def _command_history_entry_snapshot(payload: dict[str, object]) -> CommandHistoryEntrySnapshot:
    raw_arguments = payload.get("arguments", {})
    arguments_mapping = _mapping(raw_arguments) if isinstance(raw_arguments, dict) else {}
    return CommandHistoryEntrySnapshot(
        raw_command=str(payload.get("raw_command", "")),
        command_name=str(payload.get("command_name", "")),
        arguments={str(key): value for key, value in arguments_mapping.items()},
        timestamp=str(payload.get("timestamp", "")),
    )


def _mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"Expected mapping, got {type(value)!r}")
    return {str(key): item for key, item in value.items()}


def _sequence(value: object) -> list[object]:
    if not isinstance(value, list):
        raise TypeError(f"Expected list, got {type(value)!r}")
    return value


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    return float(value)


def _string_mapping(value: object) -> dict[str, str]:
    mapping = _mapping(value) if isinstance(value, dict) else {}
    return {str(key): str(item) for key, item in mapping.items()}
