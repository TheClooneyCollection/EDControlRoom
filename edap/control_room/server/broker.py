from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from typing import Any
from uuid import uuid4

from edap.control_room.protocol.events import AnnouncementEvent
from edap.control_room.protocol.sink import ControlRoomEventSink
from edap.control_room.protocol.snapshot import (
    ActivityLogEntry,
    ActiveOperatorSnapshot,
    ConnectedClientSnapshot,
    ControlRoomSnapshot,
)


@dataclass
class ObserverSession:
    session_id: str
    client_name: str
    queue: asyncio.Queue[dict[str, Any]]


class InMemoryObserverSessionBroker(ControlRoomEventSink):
    def __init__(self, *, queue_size: int = 200) -> None:
        self._queue_size = queue_size
        self._sessions: dict[str, ObserverSession] = {}
        self._latest_snapshot: ControlRoomSnapshot | None = None

    def register_observer(self, client_name: str) -> ObserverSession:
        session = ObserverSession(
            session_id=f"observer-{uuid4().hex[:12]}",
            client_name=client_name,
            queue=asyncio.Queue(maxsize=self._queue_size),
        )
        self._sessions[session.session_id] = session
        self._broadcast_current_snapshot()
        return session

    def unregister(self, session_id: str) -> None:
        removed = self._sessions.pop(session_id, None)
        if removed is not None:
            self._broadcast_current_snapshot()

    def connected_clients(self) -> list[ConnectedClientSnapshot]:
        return [
            ConnectedClientSnapshot(
                session_id=session.session_id,
                client_name=session.client_name,
                client_role="observer",
            )
            for session in self._sessions.values()
        ]

    def merge_snapshot(
        self,
        base_snapshot: ControlRoomSnapshot,
        *,
        include_local_operator: bool = True,
    ) -> ControlRoomSnapshot:
        connected_clients = list(self.connected_clients())
        if include_local_operator:
            connected_clients.insert(
                0,
                ConnectedClientSnapshot(
                    session_id=base_snapshot.session.session_id,
                    client_name=base_snapshot.active_operator.client_name
                    if base_snapshot.active_operator is not None
                    else "local-server",
                    client_role="active_operator",
                ),
            )
        return ControlRoomSnapshot(
            session=base_snapshot.session,
            connected_clients=connected_clients,
            active_operator=base_snapshot.active_operator,
            ship=base_snapshot.ship,
            market=base_snapshot.market,
            haul_session=base_snapshot.haul_session,
            ui_state=base_snapshot.ui_state,
            command_history=base_snapshot.command_history,
            prompt_state=base_snapshot.prompt_state,
            replay_browser=base_snapshot.replay_browser,
            activity_log=base_snapshot.activity_log,
            server_status=base_snapshot.server_status,
        )

    def publish_activity_log(self, entry: ActivityLogEntry) -> None:
        self._broadcast(
            {
                "message_type": "event.activity_log_appended",
                "payload": {
                    "entry": {
                        "entry_id": entry.entry_id,
                        "timestamp": entry.timestamp,
                        "message_text": entry.message_text,
                        "severity": entry.severity,
                    }
                },
            }
        )

    def publish_announcement(self, event: AnnouncementEvent) -> None:
        self._broadcast(
            {
                "message_type": "event.announcement_emitted",
                "payload": {
                    "announcement_id": event.announcement_id,
                    "message_text": event.message_text,
                    "message_values": event.message_values,
                },
            }
        )

    def publish_snapshot(self, snapshot: ControlRoomSnapshot) -> None:
        self._latest_snapshot = snapshot
        self._broadcast(
            {
                "message_type": "state.snapshot",
                "payload": asdict(self.merge_snapshot(snapshot)),
            }
        )

    def _broadcast_current_snapshot(self) -> None:
        if self._latest_snapshot is None:
            return
        self.publish_snapshot(self._latest_snapshot)

    def _broadcast(self, message: dict[str, Any]) -> None:
        for session in list(self._sessions.values()):
            if session.queue.full():
                try:
                    session.queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            session.queue.put_nowait(message)
