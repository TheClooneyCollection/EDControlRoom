from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from edap.control_room.protocol.events import AnnouncementEvent
from edap.control_room.protocol.sink import ControlRoomEventSink
from edap.control_room.protocol.snapshot import (
    ActivityLogEntry,
    ConnectedClientSnapshot,
)
from edap.control_room.server.state import ControlRoomServerState


@dataclass
class ObserverSession:
    session_id: str
    client_name: str
    client_role: str
    queue: asyncio.Queue[dict[str, Any]]


class InMemoryObserverSessionBroker(ControlRoomEventSink):
    def __init__(
        self,
        *,
        queue_size: int = 200,
        server_state: ControlRoomServerState | None = None,
    ) -> None:
        self._queue_size = queue_size
        self._sessions: dict[str, ObserverSession] = {}
        self._active_operator_session_id: str | None = None
        self._server_state = server_state or ControlRoomServerState()

    def register_observer(self, client_name: str) -> ObserverSession:
        session = ObserverSession(
            session_id=f"observer-{uuid4().hex[:12]}",
            client_name=client_name,
            client_role="observer",
            queue=asyncio.Queue(maxsize=self._queue_size),
        )
        self._sessions[session.session_id] = session
        if self._active_operator_session_id is None:
            self._active_operator_session_id = session.session_id
        return session

    def unregister(self, session_id: str) -> None:
        removed = self._sessions.pop(session_id, None)
        if removed is not None:
            if self._active_operator_session_id == session_id:
                replacement = next(iter(self._sessions.values()), None)
                self._active_operator_session_id = (
                    replacement.session_id if replacement is not None else None
                )
                self._broadcast_active_operator_changed(
                    replacement,
                    reason="active_operator_disconnected",
                )

    def connected_clients(self) -> list[ConnectedClientSnapshot]:
        return [
            ConnectedClientSnapshot(
                session_id=session.session_id,
                client_name=session.client_name,
                client_role=self._resolved_session_role(session.session_id),
            )
            for session in self._sessions.values()
        ]

    def set_active_operator_session(self, session_id: str | None) -> None:
        if session_id is not None and session_id not in self._sessions:
            raise KeyError(session_id)
        self._active_operator_session_id = session_id
        session = self._sessions.get(session_id) if session_id is not None else None
        self._broadcast_active_operator_changed(session, reason="operator_claimed")

    def current_session_role(self, session_id: str) -> str:
        return self._resolved_session_role(session_id)

    def publish_activity_log(self, entry: ActivityLogEntry) -> None:
        self._server_state.record_activity_log(entry)
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
        self._server_state.record_announcement(event)
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

    def publish_data_message(self, message: dict[str, Any]) -> None:
        self._broadcast(message)

    def _broadcast(self, message: dict[str, Any]) -> None:
        for session in list(self._sessions.values()):
            self._queue_message(session, message)

    def _broadcast_active_operator_changed(
        self,
        session: ObserverSession | None,
        *,
        reason: str,
    ) -> None:
        self._broadcast(
            {
                "message_type": "event.active_operator_changed",
                "payload": {
                    "active_operator_session_id": session.session_id if session is not None else None,
                    "active_operator_client_name": session.client_name if session is not None else None,
                    "reason": reason,
                },
            }
        )

    def _queue_message(self, session: ObserverSession, message: dict[str, Any]) -> None:
        if session.queue.full():
            try:
                session.queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        session.queue.put_nowait(message)

    def _resolved_session_role(self, session_id: str) -> str:
        if self._active_operator_session_id == session_id:
            return "active_operator"
        return "observer"
