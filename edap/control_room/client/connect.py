from __future__ import annotations

import socket

from textual.widgets import Input

from edap.control_room.app import ActivityLog, ControlRoomApp, _ALL_ROUTINE_ACTIONS, _build_log_text
from edap.control_room.backend import ControlRoomBackendEvent
from edap.control_room.client.backend import RemoteObserverBackend, fetch_remote_observer_snapshot
from edap.control_room.client.target import ObserverServerTarget, parse_observer_server_target
from edap.control_room.protocol import (
    ActivityLogAppendedEvent,
    AnnouncementEvent,
    SnapshotUpdatedEvent,
)
from edap.runtime import build_runtime_context, load_config_with_fallback
from edap.tts import parse_announcement_id


class ObserverControlRoomApp(ControlRoomApp):
    def __init__(
        self,
        ctx,
        *,
        backend: RemoteObserverBackend,
        server_target: ObserverServerTarget,
        client_name: str,
    ) -> None:
        super().__init__(ctx, backend=backend)
        self._observer_backend = backend
        self._server_target = server_target
        self._client_name = client_name

    def on_mount(self) -> None:
        self._configure_screen_widgets()
        self.title = (
            f"ED Control Room Observer - {self._server_target.host}:{self._server_target.port}"
        )
        self._backend_event_unsubscribe = self._backend.subscribe_events(self._handle_backend_event)
        self._observer_backend.start()
        self._apply_remote_snapshot(replace_activity=True)
        self._observer_backend.request_snapshot()
        self._refresh_remote_command_input()

    def on_unmount(self) -> None:
        super().on_unmount()
        self._observer_backend.close()

    def _handle_backend_event(self, event: ControlRoomBackendEvent) -> None:
        self.call_from_thread(self._apply_backend_event, event)

    def _apply_backend_event(self, event: ControlRoomBackendEvent) -> None:
        if isinstance(event, SnapshotUpdatedEvent):
            self._view_snapshot = event.snapshot
            self._apply_remote_snapshot(replace_activity=True)
            return
        if isinstance(event, ActivityLogAppendedEvent):
            self._protocol_activity_log.append(event.entry)
            if len(self._protocol_activity_log) > self._activity_log_max_lines:
                self._protocol_activity_log = self._protocol_activity_log[-self._activity_log_max_lines :]
            activity = self.query_one("#activity", ActivityLog)
            activity.write(_build_log_text(event.entry.message_text))
            self._refresh_activity_title()
            return
        if isinstance(event, AnnouncementEvent):
            self._play_local_announcement(event)

    def _apply_remote_snapshot(self, *, replace_activity: bool) -> None:
        self._sync_view_snapshot()
        self._tts.set_commander_name(self._view_snapshot.ship.commander_name)
        if replace_activity:
            self._replace_activity_log(self._view_snapshot.activity_log)
        self._refresh_status()
        self._refresh_haul_stats()
        self._refresh_market()
        self._update_resume_detail()
        self._refresh_remote_command_input()

    def _play_local_announcement(self, event: AnnouncementEvent) -> None:
        parsed_id = parse_announcement_id(event.announcement_id)
        if parsed_id is None:
            return
        self._tts.announce(parsed_id, **event.message_values)

    def _refresh_remote_command_input(self) -> None:
        command_input = self.query_one("#cmd", Input)
        is_active_operator = self._view_snapshot.session.client_role == "active_operator"
        command_input.disabled = not is_active_operator
        command_input.placeholder = (
            self._default_command_placeholder
            if is_active_operator
            else "observer mode - read only"
        )


def connect_observer_mode(
    *,
    config_path: str,
    target: str,
    access_token: str,
    client_name: str | None = None,
) -> None:
    loaded = load_config_with_fallback(config_path)
    server_target = parse_observer_server_target(target)
    resolved_client_name = (client_name or socket.gethostname()).strip() or "observer-client"
    _, snapshot = fetch_remote_observer_snapshot(
        server_target=server_target,
        access_token=access_token,
    )
    ctx = build_runtime_context(
        loaded.config,
        config_path=loaded.config_path,
        used_example_config_fallback=loaded.used_example_config_fallback,
        actions=_ALL_ROUTINE_ACTIONS,
    )
    backend = RemoteObserverBackend(
        server_target=server_target,
        access_token=access_token,
        client_name=resolved_client_name,
        initial_snapshot=snapshot,
    )
    app = ObserverControlRoomApp(
        ctx,
        backend=backend,
        server_target=server_target,
        client_name=resolved_client_name,
    )
    app.run()
