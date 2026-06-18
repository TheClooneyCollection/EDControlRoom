from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from itertools import count
from typing import Any


_message_counter = count(1)


def protocol_message(message_type: str, payload: Any, *, correlation_message_id: str | None = None) -> dict[str, Any]:
    body = asdict(payload) if is_dataclass(payload) else payload
    message = {
        "schema": "edcontrolroom.control_room_message",
        "version": 1,
        "message_type": message_type,
        "message_id": f"message-{next(_message_counter):06d}",
        "timestamp": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "payload": body,
    }
    if correlation_message_id is not None:
        message["correlation_message_id"] = correlation_message_id
    return message
