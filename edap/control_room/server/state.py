from __future__ import annotations

from dataclasses import replace

from edap.control_room.protocol.events import AnnouncementEvent
from edap.control_room.protocol.snapshot import (
    ActivityLogEntry,
    CommandHistorySnapshot,
    ControlRoomSnapshot,
    PromptStateSnapshot,
    ReplayBrowserSnapshot,
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
        self._prompt_state: PromptStateSnapshot | None = None
        self._replay_browser: ReplayBrowserSnapshot | None = None

    def merge_snapshot(self, snapshot: ControlRoomSnapshot) -> ControlRoomSnapshot:
        if not self._activity_log and snapshot.activity_log:
            self.replace_activity_log(snapshot.activity_log)
        self._capture_remote_session_defaults(snapshot)
        replay_browser = self._replay_browser or snapshot.replay_browser
        ui_state = snapshot.ui_state
        if ui_state.replay_browser_open != replay_browser.open:
            ui_state = replace(ui_state, replay_browser_open=replay_browser.open)
        return replace(
            snapshot,
            ui_state=ui_state,
            command_history=self._command_history or snapshot.command_history,
            prompt_state=self._prompt_state or snapshot.prompt_state,
            replay_browser=replay_browser,
            activity_log=list(self._activity_log),
        )

    def capture_remote_session(self, snapshot: ControlRoomSnapshot) -> None:
        self._command_history = snapshot.command_history
        self._prompt_state = snapshot.prompt_state
        self._replay_browser = snapshot.replay_browser

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
        if self._prompt_state is None:
            self._prompt_state = snapshot.prompt_state
        if self._replay_browser is None:
            self._replay_browser = snapshot.replay_browser
