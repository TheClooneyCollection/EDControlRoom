from __future__ import annotations

from dataclasses import replace

from edap.control_room.protocol.events import AnnouncementEvent
from edap.control_room.protocol.snapshot import (
    ActivityLogEntry,
    CommandHistorySnapshot,
    ControlRoomSnapshot,
)


class ControlRoomServerState:
    def __init__(
        self,
        *,
        activity_log_limit: int = 2000,
        announcement_limit: int = 100,
    ) -> None:
        self._activity_log_limit = activity_log_limit
        self._announcement_limit = announcement_limit
        self._activity_log: list[ActivityLogEntry] = []
        self._announcements: list[AnnouncementEvent] = []
        self._command_history: CommandHistorySnapshot | None = None

    def merge_snapshot(self, snapshot: ControlRoomSnapshot) -> ControlRoomSnapshot:
        if not self._activity_log and snapshot.activity_log:
            self.replace_activity_log(snapshot.activity_log)
        self._capture_remote_session_defaults(snapshot)
        return replace(
            snapshot,
            command_history=self._command_history or snapshot.command_history,
            activity_log=list(self._activity_log),
        )

    def capture_remote_session(self, snapshot: ControlRoomSnapshot) -> None:
        self._command_history = snapshot.command_history

    def replace_activity_log(self, entries: list[ActivityLogEntry]) -> None:
        self._activity_log = list(entries)[-self._activity_log_limit :]

    def record_activity_log(self, entry: ActivityLogEntry) -> None:
        self._activity_log.append(entry)
        self._activity_log = self._activity_log[-self._activity_log_limit :]

    def record_announcement(self, event: AnnouncementEvent) -> None:
        self._announcements.append(event)
        self._announcements = self._announcements[-self._announcement_limit :]

    def activity_log_entries(self) -> list[ActivityLogEntry]:
        return list(self._activity_log)

    def announcements(self) -> list[AnnouncementEvent]:
        return list(self._announcements)

    def _capture_remote_session_defaults(self, snapshot: ControlRoomSnapshot) -> None:
        if self._command_history is None:
            self._command_history = snapshot.command_history
