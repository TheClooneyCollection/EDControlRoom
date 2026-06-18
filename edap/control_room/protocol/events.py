from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .snapshot import ActivityLogEntry, ControlRoomSnapshot


@dataclass(frozen=True)
class ActivityLogAppendedEvent:
    entry: ActivityLogEntry


@dataclass(frozen=True)
class AnnouncementEvent:
    announcement_id: str
    message_text: str
    message_values: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SnapshotUpdatedEvent:
    snapshot: ControlRoomSnapshot
