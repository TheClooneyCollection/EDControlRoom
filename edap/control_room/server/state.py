from __future__ import annotations

from edap.control_room.protocol.events import ActivityLogEntry, AnnouncementEvent
from edap.inara.trade_routes import TradeRoute


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
        self._selected_trade_route: TradeRoute | None = None
        self._running_trade_route: TradeRoute | None = None

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

    def set_selected_trade_route(self, route: TradeRoute | None) -> None:
        self._selected_trade_route = route

    def selected_trade_route(self) -> TradeRoute | None:
        return self._selected_trade_route

    def set_running_trade_route(self, route: TradeRoute | None) -> None:
        self._running_trade_route = route

    def running_trade_route(self) -> TradeRoute | None:
        return self._running_trade_route
