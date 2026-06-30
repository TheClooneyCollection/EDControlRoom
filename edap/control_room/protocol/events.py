from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from edap.control_room.dependencies import ControlRoomDataReadModel
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


@dataclass(frozen=True)
class DataUpdatedEvent:
    data: ControlRoomDataReadModel
