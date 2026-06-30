from __future__ import annotations

import asyncio
import json
import threading
from collections.abc import Callable
from queue import Queue
from typing import TYPE_CHECKING, Any

import httpx
import websockets

from edap.control_room.backend import ControlRoomBackend, ControlRoomBackendEventHandler
from edap.control_room.dependencies import ControlRoomDataReadModel, ControlRoomDataSource
from edap.control_room.protocol import (
    ActivityLogEntry,
    ActivityLogAppendedEvent,
    AnnouncementEvent,
    DataUpdatedEvent,
    RemoteObserverWebSocketConnectInfo,
    build_activity_log_entry,
    data_read_model_from_message,
    event_from_message,
    is_control_room_data_message,
    protocol_timestamp_now,
    validate_remote_observer_capabilities_payload,
)
from edap.control_room_state import CommandHistoryEntry
from edap.inara.trade_routes import TradeRoute
from .target import ObserverServerTarget

if TYPE_CHECKING:
    from edap.control_room.app import ControlRoomApp


_RECONNECT_DELAY_SECONDS = 1.0
_RECONNECT_DELAY_MAX_SECONDS = 30.0
_CLIENT_LOCAL_COMMAND_VERBS = frozenset(
    {
        "haul",
        "dest",
        "set_dest",
        "home",
        "replay",
        "history",
        "commands",
        "help",
        "?",
        "market",
    }
)


def _is_client_local_command(raw: str) -> bool:
    command_raw = raw[1:].lstrip() if raw.startswith("!") else raw
    parts = command_raw.split(None, 1)
    if not parts:
        return False
    return parts[0].lower() in _CLIENT_LOCAL_COMMAND_VERBS


class RemoteObserverBackend(ControlRoomBackend):
    def __init__(
        self,
        *,
        server_target: ObserverServerTarget,
        access_token: str,
        client_name: str,
        websocket_connect_info: RemoteObserverWebSocketConnectInfo,
        data_source: RemoteObserverDataSource | None = None,
    ) -> None:
        self._server_target = server_target
        self._access_token = access_token
        self._client_name = client_name
        self._data_source = data_source
        self._websocket_connect_info = websocket_connect_info
        self._event_handlers: list[ControlRoomBackendEventHandler] = []
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._websocket: Any | None = None
        self._outgoing_messages: Queue[dict[str, object]] = Queue()
        self._message_counter = 0
        self._connected = False
        self._has_connected_once = False

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run_stream_loop, daemon=True)
        self._thread.start()

    def close(self) -> None:
        self._stop_event.set()
        self._connected = False
        self._outgoing_messages.put({})
        loop = self._loop
        websocket = self._websocket
        if loop is not None and websocket is not None:
            loop.call_soon_threadsafe(asyncio.create_task, websocket.close())
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None

    def subscribe_events(
        self,
        handler: ControlRoomBackendEventHandler,
    ) -> Callable[[], None]:
        self._event_handlers.append(handler)

        def unsubscribe() -> None:
            try:
                self._event_handlers.remove(handler)
            except ValueError:
                return

        return unsubscribe

    def publish_activity_log(self, entry: ActivityLogEntry) -> None:
        return None

    def publish_announcement(self, event: AnnouncementEvent) -> None:
        return None

    def publish_snapshot(self, snapshot) -> None:
        return None

    def submit_input(self, raw: str) -> None:
        if _is_client_local_command(raw):
            return
        self.dispatch_command(raw)

    def interrupt_active_routine(self) -> None:
        self._send_command("command.cancel_active_routine", {})

    def exit_detaches_remote_session(self) -> bool:
        return True

    def dispatch_command(self, raw: str, *, skip_delay: bool | None = None) -> None:
        if _is_client_local_command(raw):
            return
        self._send_command(
            "command.submit_input",
            {
                "raw_input": raw,
                "skip_delay": skip_delay,
            },
        )

    def dispatch_destination(
        self,
        destination: str,
        galaxy_map_settle: float,
        *,
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None:
        self._send_command(
            "command.dispatch_destination",
            {
                "destination": destination,
                "galaxy_map_settle": galaxy_map_settle,
                "skip_delay": skip_delay,
                "raw_command": raw_command,
            },
        )

    def dispatch_haul_loop(
        self,
        *,
        params: dict[str, str] | None = None,
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None:
        self._send_command(
            "command.dispatch_haul_loop",
            {
                "params": {
                    str(key): str(value)
                    for key, value in (params or {}).items()
                },
                "skip_delay": skip_delay,
                "raw_command": raw_command,
            },
        )

    def load_trade_route(
        self,
        route: TradeRoute,
        *,
        raw_command: str | None = None,
    ) -> None:
        self._emit_local_message("Observer route loading is client-local.")

    def handle_haul_prompt(self, value: str) -> None:
        self._emit_local_message("Observer session is read-only.")

    def handle_haul_confirm_prompt(self, value: str) -> None:
        self._emit_local_message("Observer session is read-only.")

    def _run_stream_loop(self) -> None:
        asyncio.run(self._stream_observer_session())

    async def _stream_observer_session(self) -> None:
        self._loop = asyncio.get_running_loop()
        reconnect_delay = _RECONNECT_DELAY_SECONDS
        while not self._stop_event.is_set():
            try:
                async with websockets.connect(
                    self._websocket_connect_info.session_url,
                    additional_headers=self._websocket_connect_info.additional_headers,
                ) as websocket:
                    was_reconnecting = self._has_connected_once and not self._connected
                    self._connected = True
                    self._has_connected_once = True
                    self._websocket = websocket
                    reconnect_delay = _RECONNECT_DELAY_SECONDS
                    if was_reconnecting:
                        self._emit_local_message("Observer connection restored.")
                    sender = asyncio.create_task(self._send_loop(websocket))
                    receiver = asyncio.create_task(self._receive_loop(websocket))
                    done, pending = await asyncio.wait(
                        {sender, receiver},
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    for task in pending:
                        task.cancel()
                    for task in done:
                        task.result()
            except Exception as exc:
                if self._stop_event.is_set():
                    break
                self._handle_connection_lost(f"Observer connection lost: {exc!s}")
                self._emit_local_message(
                    f"Reconnecting in {reconnect_delay:.1f}s..."
                )
                try:
                    await asyncio.sleep(reconnect_delay)
                except asyncio.CancelledError:
                    break
                reconnect_delay = self._next_reconnect_delay(reconnect_delay)
            finally:
                self._connected = False
                self._websocket = None
        self._loop = None

    async def _send_loop(self, websocket) -> None:
        while not self._stop_event.is_set():
            message = await asyncio.to_thread(self._outgoing_messages.get)
            if not message:
                continue
            await websocket.send(json.dumps(message))

    async def _receive_loop(self, websocket) -> None:
        async for raw_message in websocket:
            if self._stop_event.is_set():
                break
            message = json.loads(raw_message)
            if self._handle_data_message(message):
                continue
            parsed_event = event_from_message(message)
            if parsed_event is not None:
                self._emit(parsed_event)
                continue
            self._handle_response_message(message)

    def _handle_data_message(self, message: dict[str, object]) -> bool:
        if not is_control_room_data_message(message):
            return False
        if self._data_source is None:
            return True
        data = data_read_model_from_message(message)
        self._data_source.hydrate(data)
        self._emit(DataUpdatedEvent(data=data))
        return True

    def _handle_response_message(self, message: dict[str, object]) -> None:
        message_type = str(message.get("message_type", ""))
        payload_value = message.get("payload", {})
        payload = payload_value if isinstance(payload_value, dict) else {}
        if message_type == "response.error":
            error_message = str(payload.get("error_message", "Remote command failed."))
            self._emit_local_message(error_message)
            return
        if message_type == "response.success":
            message_text = str(payload.get("message_text", "")).strip()
            if message_text:
                self._emit_local_message(message_text)

    def request_active_operator(self) -> None:
        self._send_command(
            "command.request_active_operator",
            {},
        )

    def _emit_local_message(self, text: str) -> None:
        self._emit(ActivityLogAppendedEvent(entry=build_activity_log_entry(text)))

    def _handle_connection_lost(self, text: str) -> None:
        self._connected = False
        self._emit_local_message(text)

    def _next_reconnect_delay(self, delay_seconds: float) -> float:
        return min(delay_seconds * 2.0, _RECONNECT_DELAY_MAX_SECONDS)

    def _send_command(self, message_type: str, payload: dict[str, object]) -> None:
        if not self._connected and self._has_connected_once:
            self._emit_local_message("Observer connection unavailable.")
            return
        self._message_counter += 1
        self._outgoing_messages.put(
            {
                "schema": "edcontrolroom.control_room_message",
                "version": 1,
                "message_type": message_type,
                "message_id": f"client-message-{self._message_counter:06d}",
                "timestamp": protocol_timestamp_now(),
                "payload": payload,
            }
        )

    def _emit(self, event: object) -> None:
        for handler in list(self._event_handlers):
            handler(event)  # type: ignore[arg-type]


class RemoteObserverExecution:
    def __init__(self, backend: RemoteObserverBackend) -> None:
        self._backend = backend
        self._app: ControlRoomApp | None = None

    def bind_app(self, app: ControlRoomApp) -> None:
        self._app = app

    def submit_command(self, raw: str, *, skip_delay: bool | None = None) -> None:
        if _is_client_local_command(raw):
            app = self._require_app()
            from edap.control_room import commands as _commands

            _commands.dispatch(app, raw, skip_delay_override=skip_delay)
            return
        self._backend.dispatch_command(raw, skip_delay=skip_delay)

    def dispatch_destination(
        self,
        destination: str,
        galaxy_map_settle: float,
        *,
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None:
        self._backend.dispatch_destination(
            destination,
            galaxy_map_settle,
            skip_delay=skip_delay,
            raw_command=raw_command,
        )

    def dispatch_haul_loop(
        self,
        *,
        params: dict[str, str] | None = None,
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None:
        self._backend.dispatch_haul_loop(
            params=params,
            skip_delay=skip_delay,
            raw_command=raw_command,
        )

    def load_trade_route(
        self,
        route: TradeRoute,
        *,
        raw_command: str | None = None,
    ) -> None:
        self._require_app()._facade.load_trade_route(route, raw_command=raw_command)

    def handle_haul_prompt(self, value: str) -> None:
        app = self._require_app()
        from edap.control_room import prompts as _prompts

        _prompts.handle_haul_prompt(
            app,
            value,
            default_placeholder=app._default_command_placeholder,
        )

    def handle_haul_confirm_prompt(self, value: str) -> None:
        app = self._require_app()
        from edap.control_room import prompts as _prompts

        _prompts.handle_haul_confirm_prompt(
            app,
            value,
            default_placeholder=app._default_command_placeholder,
        )

    def cancel_active_routine(self) -> None:
        self._backend.interrupt_active_routine()

    def _require_app(self) -> ControlRoomApp:
        if self._app is None:
            raise RuntimeError("Remote observer execution is not bound to an app.")
        return self._app


class RemoteObserverDataSource(ControlRoomDataSource):
    def __init__(self, initial_data: ControlRoomDataReadModel) -> None:
        self._data = initial_data
        self._lock = threading.Lock()

    def current(self) -> ControlRoomDataReadModel:
        with self._lock:
            return self._data

    def hydrate(self, data: ControlRoomDataReadModel) -> None:
        with self._lock:
            self._data = data


def fetch_remote_control_room_data(
    *,
    server_target: ObserverServerTarget,
    access_token: str,
) -> tuple[dict[str, Any], ControlRoomDataReadModel]:
    auth_headers = {"Authorization": f"Bearer {access_token}"}
    with httpx.Client(timeout=10.0) as client:
        capabilities_response = client.get(
            f"{server_target.http_base_url}/capabilities",
            headers=auth_headers,
        )
        _raise_for_auth_or_http_error(capabilities_response, server_target)
        capabilities = capabilities_response.json()
        _validate_remote_observer_capabilities(capabilities, server_target)

        hydrate_response = client.get(
            f"{server_target.http_base_url}/hydrate",
            headers=auth_headers,
        )
        _raise_for_auth_or_http_error(hydrate_response, server_target)
        data = data_read_model_from_message(hydrate_response.json())
    return capabilities, data


def _raise_for_auth_or_http_error(
    response: httpx.Response,
    server_target: ObserverServerTarget,
) -> None:
    if response.status_code == 401:
        raise SystemExit(
            f"Authentication failed for {server_target.host}:{server_target.port}. "
            "Check the shared access token."
        )
    response.raise_for_status()


def _validate_remote_observer_capabilities(
    capabilities: dict[str, Any],
    server_target: ObserverServerTarget,
) -> None:
    validation_error = validate_remote_observer_capabilities_payload(capabilities)
    if validation_error is None:
        return
    if validation_error.startswith(
        (
            "supported_command_message_types",
            "supported_event_message_types",
            "supported_response_message_types",
            "supported_message_types",
            "supported_client_roles",
            "authentication_supported_transports",
            "message_schema_url",
            "browser_probe_url",
        )
    ):
        raise SystemExit(
            f"Remote server {server_target.host}:{server_target.port} returned invalid capabilities: "
            f"{validation_error}"
        )
    raise SystemExit(
        f"Remote server {server_target.host}:{server_target.port} {validation_error}"
    )
