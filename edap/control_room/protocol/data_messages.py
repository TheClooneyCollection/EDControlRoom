from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from itertools import count
from typing import Any

from edap.control_room.dependencies import ControlRoomDataReadModel


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
