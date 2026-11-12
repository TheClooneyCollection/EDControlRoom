from __future__ import annotations

from datetime import UTC, datetime
from itertools import count
from typing import Any

from .events import ActivityLogEntry, AnnouncementEvent


_activity_log_counter = count(1)


def protocol_timestamp_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_activity_log_entry(message_markup: str) -> ActivityLogEntry:
    return ActivityLogEntry(
        entry_id=f"activity-{next(_activity_log_counter):06d}",
        timestamp=protocol_timestamp_now(),
        message_text=message_markup,
        severity=None,
    )


def build_announcement_event(
    *,
    announcement_id: str,
    message_text: str,
    message_values: dict[str, Any],
) -> AnnouncementEvent:
    return AnnouncementEvent(
        announcement_id=announcement_id,
        message_text=message_text,
        message_values=message_values,
    )
