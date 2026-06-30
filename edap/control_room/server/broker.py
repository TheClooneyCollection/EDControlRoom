from __future__ import annotations

import asyncio
from dataclasses import dataclass
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
        self._latest_snapshot: ControlRoomSnapshot | None = None
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

    def current_snapshot(
        self,
        *,
        snapshot_provider,
        session_id: str | None = None,
    ) -> ControlRoomSnapshot:
        base_snapshot = self._latest_snapshot
        if base_snapshot is None:
            base_snapshot = self.merge_snapshot(snapshot_provider())
            self._latest_snapshot = base_snapshot
        return self.merge_snapshot(base_snapshot, session_id=session_id)

    def merge_snapshot(
        self,
        base_snapshot: ControlRoomSnapshot,
        *,
        session_id: str | None = None,
        include_local_operator: bool = True,
    ) -> ControlRoomSnapshot:
        base_snapshot = self._server_state.merge_snapshot(base_snapshot)
        connected_clients = list(self.connected_clients())
        active_operator = base_snapshot.active_operator
        if self._active_operator_session_id is None and include_local_operator:
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
        elif self._active_operator_session_id is not None:
            active_session = self._sessions.get(self._active_operator_session_id)
            if active_session is not None:
                active_operator = ActiveOperatorSnapshot(
                    session_id=active_session.session_id,
                    client_name=active_session.client_name,
                )

        session_role = base_snapshot.session.client_role
        if session_id is not None:
            session_role = self._resolved_session_role(session_id)
        return ControlRoomSnapshot(
            session=type(base_snapshot.session)(
                session_id=session_id or base_snapshot.session.session_id,
                client_role=session_role,
            ),
            connected_clients=connected_clients,
            active_operator=active_operator,
            ship=base_snapshot.ship,
            market=base_snapshot.market,
            haul_session=base_snapshot.haul_session,
            ui_state=base_snapshot.ui_state,
            command_history=base_snapshot.command_history,
            activity_log=base_snapshot.activity_log,
            server_status=base_snapshot.server_status,
            trade_routes=base_snapshot.trade_routes,
        )

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

    def publish_snapshot(self, snapshot: ControlRoomSnapshot) -> None:
        self._server_state.capture_remote_session(snapshot)
        resolved_snapshot = self._server_state.merge_snapshot(snapshot)
        self._latest_snapshot = resolved_snapshot

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
