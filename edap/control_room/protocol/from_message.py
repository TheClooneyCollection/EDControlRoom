from __future__ import annotations

from .events import ActivityLogAppendedEvent, ActivityLogEntry, AnnouncementEvent


def event_from_message(
    message: dict[str, object],
) -> ActivityLogAppendedEvent | AnnouncementEvent | None:
    message_type = str(message.get("message_type", ""))
    payload = _mapping(message.get("payload", {}))
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


def _activity_log_entry(payload: dict[str, object]) -> ActivityLogEntry:
    return ActivityLogEntry(
        entry_id=str(payload["entry_id"]),
        timestamp=str(payload["timestamp"]),
        message_text=str(payload["message_text"]),
        severity=_optional_str(payload.get("severity")),
    )


def _mapping(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return value
    raise ValueError(f"Expected object mapping, got {type(value).__name__}.")


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
