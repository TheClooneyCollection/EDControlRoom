from __future__ import annotations

from typing import Protocol

from .events import AnnouncementEvent
from .snapshot import ActivityLogEntry


class ControlRoomEventSink(Protocol):
    def publish_activity_log(self, entry: ActivityLogEntry) -> None: ...

    def publish_announcement(self, event: AnnouncementEvent) -> None: ...

    def publish_data_refresh(self) -> None: ...
