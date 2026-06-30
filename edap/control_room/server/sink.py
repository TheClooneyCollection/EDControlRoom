from __future__ import annotations

import logging
from typing import Callable, Iterable

from rich.text import Text

from edap.control_room.protocol.events import AnnouncementEvent
from edap.control_room.protocol import hydrate_message
from edap.control_room.protocol.sink import ControlRoomEventSink
from edap.control_room.protocol import ActivityLogEntry
from edap.control_room.server.broker import InMemoryObserverSessionBroker


class FanoutControlRoomEventSink(ControlRoomEventSink):
    def __init__(self, sinks: Iterable[ControlRoomEventSink]) -> None:
        self._sinks = list(sinks)

    def publish_activity_log(self, entry: ActivityLogEntry) -> None:
        for sink in self._sinks:
            sink.publish_activity_log(entry)

    def publish_announcement(self, event: AnnouncementEvent) -> None:
        for sink in self._sinks:
            sink.publish_announcement(event)

    def publish_data_refresh(self) -> None:
        for sink in self._sinks:
            sink.publish_data_refresh()


class ServerActivityLogSink(ControlRoomEventSink):
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger("edap.control_room.server.activity")

    def publish_activity_log(self, entry: ActivityLogEntry) -> None:
        self._logger.info("%s", Text.from_markup(entry.message_text).plain)

    def publish_announcement(self, event: AnnouncementEvent) -> None:
        return None

    def publish_data_refresh(self) -> None:
        return None


class DataHydrateFanoutSink(ControlRoomEventSink):
    def __init__(
        self,
        *,
        data_provider: Callable[[], object],
        broker: InMemoryObserverSessionBroker,
    ) -> None:
        self._data_provider = data_provider
        self._broker = broker

    def publish_activity_log(self, entry: ActivityLogEntry) -> None:
        return None

    def publish_announcement(self, event: AnnouncementEvent) -> None:
        return None

    def publish_data_refresh(self) -> None:
        self._broker.publish_data_message(hydrate_message(self._data_provider()))
