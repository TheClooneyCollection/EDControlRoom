from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from itertools import count
from typing import Any

from edap.control_room.dependencies import (
    ActivityLogItem,
    ActivityLogReadModel,
    CommandHistoryReadModel,
    ControlRoomDataReadModel,
    RoutineReadModel,
    ServerStatusReadModel,
    SessionReadModel,
)
from edap.control_room.models import HaulStats, MarketData, ShipState
from edap.control_room_state import CommandHistoryEntry


DATA_MESSAGE_SCHEMA = "edcontrolroom.control_room_data_message"
DATA_MESSAGE_VERSION = 1

CONTROL_ROOM_HYDRATE = "control_room.hydrate"
SHIP_UPDATED = "ship.updated"
MARKET_UPDATED = "market.updated"
HAUL_UPDATED = "haul.updated"
HISTORY_UPDATED = "history.updated"
ACTIVITY_APPENDED = "activity.appended"
SESSION_UPDATED = "session.updated"
ROUTINE_UPDATED = "routine.updated"

SUPPORTED_DATA_MESSAGE_TYPES = [
    CONTROL_ROOM_HYDRATE,
    SHIP_UPDATED,
    MARKET_UPDATED,
    HAUL_UPDATED,
    HISTORY_UPDATED,
    ACTIVITY_APPENDED,
    SESSION_UPDATED,
    ROUTINE_UPDATED,
]

_data_message_counter = count(1)


def data_protocol_timestamp_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def control_room_data_message(
    message_type: str,
    payload: Any,
    *,
    correlation_message_id: str | None = None,
) -> dict[str, Any]:
    body = asdict(payload) if is_dataclass(payload) else payload
    message = {
        "schema": DATA_MESSAGE_SCHEMA,
        "version": DATA_MESSAGE_VERSION,
        "message_type": message_type,
        "message_id": f"data-message-{next(_data_message_counter):06d}",
        "timestamp": data_protocol_timestamp_now(),
        "payload": body,
    }
    if correlation_message_id is not None:
        message["correlation_message_id"] = correlation_message_id
    return message


def hydrate_message(data: ControlRoomDataReadModel) -> dict[str, Any]:
    return control_room_data_message(CONTROL_ROOM_HYDRATE, data)


def is_control_room_data_message(message: dict[str, Any]) -> bool:
    return (
        message.get("schema") == DATA_MESSAGE_SCHEMA
        and message.get("version") == DATA_MESSAGE_VERSION
        and message.get("message_type") in SUPPORTED_DATA_MESSAGE_TYPES
    )


def data_read_model_from_message(message: dict[str, Any]) -> ControlRoomDataReadModel:
    if not is_control_room_data_message(message):
        raise ValueError("Not a supported Control Room data message.")
    if message.get("message_type") != CONTROL_ROOM_HYDRATE:
        raise ValueError(f"Unsupported data read model message type: {message.get('message_type')!r}")
    payload = _mapping(message.get("payload", {}))
    return data_read_model_from_payload(payload)


def data_read_model_from_payload(payload: dict[str, Any]) -> ControlRoomDataReadModel:
    return ControlRoomDataReadModel(
        ship=_ship(_mapping(payload.get("ship", {}))),
        market=_market(_mapping(payload.get("market", {}))),
        haul_session=_haul_stats(_mapping(payload.get("haul_session", {}))),
        command_history=_command_history(_mapping(payload.get("command_history", {}))),
        activity_log=_activity_log(_mapping(payload.get("activity_log", {}))),
        routine=_routine(_mapping(payload.get("routine", {}))),
        session=_session(_mapping(payload.get("session", {}))),
        server_status=_server_status(_mapping(payload.get("server_status", {}))),
    )


def _ship(payload: dict[str, Any]) -> ShipState:
    return ShipState(
        commander=_optional_str(payload.get("commander")),
        ship_type=_optional_str(payload.get("ship_type")),
        system=_optional_str(payload.get("system")),
        station=_optional_str(payload.get("station")),
        status=_optional_str(payload.get("status")),
        fuel_level=_optional_float(payload.get("fuel_level")),
        fuel_capacity=_optional_float(payload.get("fuel_capacity")),
        credits=_optional_int(payload.get("credits")),
        cargo_count=_int(payload.get("cargo_count"), 0),
        cargo_capacity=_optional_int(payload.get("cargo_capacity")),
        cargo_inventory=list(payload.get("cargo_inventory", []))
        if isinstance(payload.get("cargo_inventory"), list)
        else [],
        target=_optional_str(payload.get("target")),
        destination_system=_optional_str(payload.get("destination_system")),
        destination_body=_optional_str(payload.get("destination_body")),
        destination_name=_optional_str(payload.get("destination_name")),
    )


def _market(payload: dict[str, Any]) -> MarketData:
    return MarketData(
        station=str(payload.get("station", "")),
        system=str(payload.get("system", "")),
        timestamp=str(payload.get("timestamp", "")),
        items=list(payload.get("items", [])) if isinstance(payload.get("items"), list) else [],
        locked=bool(payload.get("locked", False)),
    )


def _haul_stats(payload: dict[str, Any]) -> HaulStats:
    return HaulStats(
        station_1_buying=str(payload.get("station_1_buying", "")),
        station_2_buying=str(payload.get("station_2_buying", "")),
        station_1=str(payload.get("station_1", "")),
        station_2=str(payload.get("station_2", "")),
        session_started_at=_optional_float(payload.get("session_started_at")),
        session_elapsed_s=_float(payload.get("session_elapsed_s"), 0.0),
        session_active=bool(payload.get("session_active", False)),
        active=bool(payload.get("active", False)),
        clean_run_active=bool(payload.get("clean_run_active", False)),
        waiting_for_station_1_departure=bool(payload.get("waiting_for_station_1_departure", False)),
        resumed_mid_run=bool(payload.get("resumed_mid_run", False)),
        docked_back_at_station_1=bool(payload.get("docked_back_at_station_1", False)),
        current_run_started_at=_optional_float(payload.get("current_run_started_at")),
        current_run_elapsed_s=_optional_float(payload.get("current_run_elapsed_s")),
        current_run_profit=_int(payload.get("current_run_profit"), 0),
        completed_runs=_int(payload.get("completed_runs"), 0),
        accumulated_profit=_int(payload.get("accumulated_profit"), 0),
        last_run_profit=_optional_int(payload.get("last_run_profit")),
        last_run_elapsed_s=_optional_float(payload.get("last_run_elapsed_s")),
        total_run_elapsed_s=_float(payload.get("total_run_elapsed_s"), 0.0),
    )


def _command_history(payload: dict[str, Any]) -> CommandHistoryReadModel:
    raw_entries = payload.get("history_entries", [])
    entries = raw_entries if isinstance(raw_entries, list) else []
    return CommandHistoryReadModel(
        default_haul={
            str(key): str(value)
            for key, value in _mapping(payload.get("default_haul", {})).items()
        },
        history_entries=tuple(
            CommandHistoryEntry(
                raw=str(_mapping(entry).get("raw", "")),
                command=str(_mapping(entry).get("command", "")),
                params={
                    str(key): str(value)
                    for key, value in _mapping(_mapping(entry).get("params", {})).items()
                },
                timestamp=str(_mapping(entry).get("timestamp", "")),
            )
            for entry in entries
        ),
        history_limit=_int(payload.get("history_limit"), 0),
    )


def _activity_log(payload: dict[str, Any]) -> ActivityLogReadModel:
    raw_entries = payload.get("entries", [])
    entries = raw_entries if isinstance(raw_entries, list) else []
    return ActivityLogReadModel(
        entries=tuple(
            ActivityLogItem(
                entry_id=str(_mapping(entry).get("entry_id", "")),
                timestamp=str(_mapping(entry).get("timestamp", "")),
                message_text=str(_mapping(entry).get("message_text", "")),
                severity=str(_mapping(entry).get("severity", "info")),
            )
            for entry in entries
        )
    )


def _routine(payload: dict[str, Any]) -> RoutineReadModel:
    return RoutineReadModel(
        routine_active=bool(payload.get("routine_active", False)),
        active_routine_name=_optional_str(payload.get("active_routine_name")),
        haul_stop_requested=bool(payload.get("haul_stop_requested", False)),
        verbose_controls=bool(payload.get("verbose_controls", False)),
        instant_mode=bool(payload.get("instant_mode", False)),
        shutdown_requested=bool(payload.get("shutdown_requested", False)),
        shutdown_finalized=bool(payload.get("shutdown_finalized", False)),
    )


def _session(payload: dict[str, Any]) -> SessionReadModel:
    return SessionReadModel(
        session_id=str(payload.get("session_id", "")),
        client_role=str(payload.get("client_role", "")),
        client_name=str(payload.get("client_name", "")),
        active_operator_name=_optional_str(payload.get("active_operator_name")),
    )


def _server_status(payload: dict[str, Any]) -> ServerStatusReadModel:
    capability_names = payload.get("capability_names", ())
    return ServerStatusReadModel(
        server_name=str(payload.get("server_name", "")),
        server_version=str(payload.get("server_version", "")),
        runtime_platform=str(payload.get("runtime_platform", "")),
        journal_source_status=str(payload.get("journal_source_status", "")),
        bindings_source_status=str(payload.get("bindings_source_status", "")),
        bindings_loaded=bool(payload.get("bindings_loaded", False)),
        capability_names=tuple(str(item) for item in capability_names)
        if isinstance(capability_names, (list, tuple))
        else (),
        operator_mode=str(payload.get("operator_mode", "")),
    )


def _mapping(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _int(value: object, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    return _int(value, 0)


def _float(value: object, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    return _float(value, 0.0)
