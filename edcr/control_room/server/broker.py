from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Callable
from uuid import uuid4

from edcr.control_room.protocol.events import AnnouncementEvent
from edcr.control_room.protocol.sink import ControlRoomEventSink
from edcr.control_room.protocol import ActivityLogEntry
from edcr.control_room.server.messages import protocol_message
from edcr.control_room.server.state import ControlRoomServerState


@dataclass(frozen=True)
class ConnectedClient:
    session_id: str
    client_name: str
    client_role: str


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
        # Callbacks that get every broadcast as a protocol message: a peer streams them to hub pages.
        self._listeners: dict[str, Callable[[dict[str, Any]], None]] = {}
        self._server_state = server_state or ControlRoomServerState()
        # Set while the hub voices this node with its speakers muted (`edcr.hub.voice`): announcements
        # carry `muted`, so this node's pages and TUIs do not speak them either.
        self._callouts_muted = False

    def register_observer(self, client_name: str) -> ObserverSession:
        session = ObserverSession(
            session_id=f"observer-{uuid4().hex[:12]}",
            client_name=client_name,
            client_role="active_operator",
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

    def add_listener(self, deliver: Callable[[dict[str, Any]], None]) -> Callable[[], None]:
        """Call `deliver` with every broadcast, on the publishing thread; returns the remover."""
        listener_id = uuid4().hex
        self._listeners[listener_id] = deliver

        def remove() -> None:
            self._listeners.pop(listener_id, None)

        return remove

    def connected_clients(self) -> list[ConnectedClient]:
        return [
            ConnectedClient(
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

    def mute_callouts(self, muted: bool) -> None:
        self._callouts_muted = muted

    @property
    def callouts_muted(self) -> bool:
        return self._callouts_muted

    def publish_announcement(self, event: AnnouncementEvent) -> None:
        self._server_state.record_announcement(event)
        payload: dict[str, Any] = {
            "announcement_id": event.announcement_id,
            "message_text": event.message_text,
            "message_values": event.message_values,
        }
        if self._callouts_muted or event.muted:
            payload["muted"] = True
        self._broadcast({"message_type": "event.announcement_emitted", "payload": payload})

    def publish_data_message(self, message: dict[str, Any]) -> None:
        self._broadcast(message)

    @property
    def server_state(self) -> ControlRoomServerState:
        return self._server_state

    def _broadcast(self, message: dict[str, Any]) -> None:
        for session in list(self._sessions.values()):
            self._queue_message(session, message)
        if self._listeners:
            framed = message if "schema" in message else protocol_message(message["message_type"], message["payload"])
            for deliver in list(self._listeners.values()):
                deliver(framed)

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
        if session_id in self._sessions:
            return "active_operator"
        return "observer"
