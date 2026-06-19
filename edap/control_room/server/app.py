from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from pathlib import Path
from typing import Callable

from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect

from edap.control_room.server.auth import ObserverServerAuth
from edap.control_room.server.broker import InMemoryObserverSessionBroker
from edap.control_room.server.commands import (
    ObserverSessionCommandHandler,
    command_history_entry_from_payload,
)
from edap.control_room.protocol import (
    SUPPORTED_COMMAND_MESSAGE_TYPES,
    SUPPORTED_EVENT_MESSAGE_TYPES,
    SUPPORTED_MESSAGE_TYPES,
    SUPPORTED_RESPONSE_MESSAGE_TYPES,
    build_remote_observer_capabilities_payload,
)
from edap.control_room.server.messages import protocol_message

MESSAGE_SCHEMA_URL_PATH = "/schema/control_room_message.json"
BROWSER_PROBE_URL_PATH = "/browser-probe"
_MESSAGE_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3] / "docs" / "schemas" / "control_room_message.schema.json"
)
_BROWSER_PROBE_PATH = (
    Path(__file__).resolve().parents[3] / "tools" / "scratch" / "control_room_remote_browser.html"
)
CONTROL_ROOM_MESSAGE_SCHEMA = json.loads(_MESSAGE_SCHEMA_PATH.read_text(encoding="utf-8"))
CONTROL_ROOM_BROWSER_PROBE_HTML = _BROWSER_PROBE_PATH.read_text(encoding="utf-8")


def build_observer_server_app(
    *,
    snapshot_provider: Callable[[], object],
    command_handler: ObserverSessionCommandHandler | None,
    broker: InMemoryObserverSessionBroker,
    auth: ObserverServerAuth,
) -> Starlette:
    def unauthorized_response() -> JSONResponse:
        return JSONResponse(
            {"detail": "authentication required"},
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
        )

    def require_http_auth(request: Request) -> JSONResponse | None:
        if auth.is_http_request_authorized(request):
            return None
        return unauthorized_response()

    async def health(request):
        snapshot = broker.current_snapshot(snapshot_provider=snapshot_provider)
        auth_description = auth.describe()
        return JSONResponse(
            {
                "status": "ok",
                "server_name": snapshot.server_status.server_name,
                "server_version": snapshot.server_status.server_version,
                "observer_mode": True,
                "authentication_required": auth_description.authentication_required,
            }
        )

    async def capabilities(request):
        auth_failure = require_http_auth(request)
        if auth_failure is not None:
            return auth_failure
        snapshot = broker.current_snapshot(snapshot_provider=snapshot_provider)
        auth_description = auth.describe()
        return JSONResponse(
            build_remote_observer_capabilities_payload(
                capability_names=snapshot.server_status.capability_names,
                server_version=snapshot.server_status.server_version,
                authentication_required=auth_description.authentication_required,
                authentication_scheme=auth_description.authentication_scheme,
                authentication_supported_transports=auth_description.supported_transports,
                authentication_query_parameter_name=auth_description.query_parameter_name,
                message_schema_url=MESSAGE_SCHEMA_URL_PATH,
                browser_probe_url=BROWSER_PROBE_URL_PATH,
            )
        )

    async def snapshot(request):
        auth_failure = require_http_auth(request)
        if auth_failure is not None:
            return auth_failure
        return JSONResponse(asdict(broker.current_snapshot(snapshot_provider=snapshot_provider)))

    async def message_schema(request):
        return JSONResponse(CONTROL_ROOM_MESSAGE_SCHEMA)

    async def browser_probe(request):
        return HTMLResponse(CONTROL_ROOM_BROWSER_PROBE_HTML)

    async def session(websocket: WebSocket) -> None:
        if not auth.is_websocket_authorized(websocket):
            await websocket.close(code=4401, reason="authentication required")
            return
        client_name = websocket.query_params.get("client_name", "observer-client")
        await websocket.accept()
        observer = broker.register_observer(client_name)
        merged_snapshot = broker.current_snapshot(snapshot_provider=snapshot_provider)
        try:
            await websocket.send_json(
                protocol_message(
                    "event.connection_ready",
                    {
                        "session_id": observer.session_id,
                        "server_name": merged_snapshot.server_status.server_name,
                        "server_version": merged_snapshot.server_status.server_version,
                        "client_role": broker.current_session_role(observer.session_id),
                        "capability_names": merged_snapshot.server_status.capability_names,
                    },
                )
            )
            broker.publish_snapshot(snapshot_provider())
            sender = asyncio.create_task(_send_session_messages(websocket, observer))
            receiver = asyncio.create_task(
                _receive_session_messages(
                    websocket,
                    observer=observer,
                    snapshot_provider=snapshot_provider,
                    command_handler=command_handler,
                    broker=broker,
                )
            )
            done, pending = await asyncio.wait(
                {sender, receiver},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            for task in done:
                task.result()
        except WebSocketDisconnect:
            pass
        finally:
            broker.unregister(observer.session_id)
            broker.publish_snapshot(snapshot_provider())

    app = Starlette(
        routes=[
            Route("/health", health),
            Route("/capabilities", capabilities),
            Route("/snapshot", snapshot),
            Route(MESSAGE_SCHEMA_URL_PATH, message_schema),
            Route(BROWSER_PROBE_URL_PATH, browser_probe),
            WebSocketRoute("/session", session),
        ]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    return app


async def _send_session_messages(websocket: WebSocket, observer) -> None:
    while True:
        message = await observer.queue.get()
        await websocket.send_json(protocol_message(message["message_type"], message["payload"]))


async def _receive_session_messages(
    websocket: WebSocket,
    *,
    observer,
    snapshot_provider: Callable[[], object],
    command_handler: ObserverSessionCommandHandler | None,
    broker: InMemoryObserverSessionBroker,
) -> None:
    while True:
        message = await websocket.receive_json()
        response = _handle_session_message(
            message,
            session_id=observer.session_id,
            client_role=broker.current_session_role(observer.session_id),
            snapshot_provider=snapshot_provider,
            command_handler=command_handler,
            broker=broker,
        )
        if response is None:
            continue
        await websocket.send_json(response)


def _handle_session_message(
    message: dict[str, object],
    *,
    session_id: str,
    client_role: str,
    snapshot_provider: Callable[[], object],
    command_handler: ObserverSessionCommandHandler | None,
    broker: InMemoryObserverSessionBroker,
) -> dict[str, object] | None:
    message_type = str(message.get("message_type", ""))
    message_id = message.get("message_id")
    correlation_message_id = str(message_id) if message_id is not None else None
    payload_value = message.get("payload", {})
    payload = payload_value if isinstance(payload_value, dict) else {}

    if message_type == "command.request_snapshot":
        return protocol_message(
            "state.snapshot",
            asdict(
                broker.current_snapshot(
                    snapshot_provider=snapshot_provider,
                    session_id=session_id,
                )
            ),
            correlation_message_id=correlation_message_id,
        )

    if message_type == "command.request_active_operator":
        broker.set_active_operator_session(session_id)
        return protocol_message(
            "response.success",
            {
                "accepted": True,
                "message_text": "Active operator role assigned.",
                "result": {"client_role": "active_operator"},
            },
            correlation_message_id=correlation_message_id,
        )

    if message_type == "command.submit_input":
        if client_role != "active_operator":
            return protocol_message(
                "response.error",
                {
                    "error_code": "observer_read_only",
                    "error_message": "Observer clients cannot issue operator commands.",
                    "recommended_action": "Use an active operator session to run commands.",
                    "retryable": False,
                },
                correlation_message_id=correlation_message_id,
            )
        raw_input = payload.get("raw_input")
        if not isinstance(raw_input, str):
            return protocol_message(
                "response.error",
                {
                    "error_code": "invalid_command",
                    "error_message": "Command input must include raw_input text.",
                    "recommended_action": "Send a raw_input string.",
                    "retryable": True,
                },
                correlation_message_id=correlation_message_id,
            )
        if command_handler is None:
            return protocol_message(
                "response.error",
                {
                    "error_code": "active_operator_transport_unavailable",
                    "error_message": "Remote active-operator command execution is not available yet.",
                    "recommended_action": "Keep using embedded local mode for operator commands until promotion lands.",
                    "retryable": False,
                },
                correlation_message_id=correlation_message_id,
            )
        try:
            skip_delay_value = payload.get("skip_delay")
            skip_delay = skip_delay_value if isinstance(skip_delay_value, bool) else None
            command_handler.submit_input(raw_input, skip_delay=skip_delay)
        except Exception as exc:
            return protocol_message(
                "response.error",
                {
                    "error_code": "command_execution_failed",
                    "error_message": str(exc) or "Remote command execution failed.",
                    "recommended_action": "Check the command and server activity log, then try again.",
                    "retryable": True,
                },
                correlation_message_id=correlation_message_id,
            )
        return protocol_message(
            "response.success",
            {
                "accepted": True,
                "message_text": "Command accepted.",
                "result": {"raw_input": raw_input},
            },
            correlation_message_id=correlation_message_id,
        )

    if message_type == "command.open_replay_browser":
        if client_role != "active_operator":
            return _observer_read_only_error(correlation_message_id)
        if command_handler is None:
            return _transport_unavailable_error(correlation_message_id)
        try:
            command_handler.open_replay_browser()
        except Exception as exc:
            return _command_execution_failed_error(exc, correlation_message_id)
        return protocol_message(
            "response.success",
            {"accepted": True, "message_text": "Replay browser opened."},
            correlation_message_id=correlation_message_id,
        )

    if message_type == "command.close_replay_browser":
        if client_role != "active_operator":
            return _observer_read_only_error(correlation_message_id)
        if command_handler is None:
            return _transport_unavailable_error(correlation_message_id)
        try:
            command_handler.close_replay_browser()
        except Exception as exc:
            return _command_execution_failed_error(exc, correlation_message_id)
        return protocol_message(
            "response.success",
            {"accepted": True, "message_text": "Replay browser closed."},
            correlation_message_id=correlation_message_id,
        )

    if message_type == "command.set_replay_filter":
        if client_role != "active_operator":
            return _observer_read_only_error(correlation_message_id)
        if command_handler is None:
            return _transport_unavailable_error(correlation_message_id)
        filter_text = payload.get("filter_text")
        if not isinstance(filter_text, str):
            return protocol_message(
                "response.error",
                {
                    "error_code": "invalid_command",
                    "error_message": "Replay filter commands must include filter_text.",
                    "recommended_action": "Send a filter_text string.",
                    "retryable": True,
                },
                correlation_message_id=correlation_message_id,
            )
        try:
            command_handler.set_replay_filter(filter_text)
        except Exception as exc:
            return _command_execution_failed_error(exc, correlation_message_id)
        return protocol_message(
            "response.success",
            {"accepted": True, "message_text": "Replay filter updated."},
            correlation_message_id=correlation_message_id,
        )

    if message_type == "command.move_replay_selection":
        if client_role != "active_operator":
            return _observer_read_only_error(correlation_message_id)
        if command_handler is None:
            return _transport_unavailable_error(correlation_message_id)
        offset = payload.get("offset")
        if not isinstance(offset, int):
            return protocol_message(
                "response.error",
                {
                    "error_code": "invalid_command",
                    "error_message": "Replay selection commands must include integer offset.",
                    "recommended_action": "Send an integer offset such as -1 or 1.",
                    "retryable": True,
                },
                correlation_message_id=correlation_message_id,
            )
        try:
            command_handler.move_replay_selection(offset)
        except Exception as exc:
            return _command_execution_failed_error(exc, correlation_message_id)
        return protocol_message(
            "response.success",
            {"accepted": True, "message_text": "Replay selection moved."},
            correlation_message_id=correlation_message_id,
        )

    if message_type in {"command.replay_history_entry", "command.toggle_replay_default_haul"}:
        if client_role != "active_operator":
            return _observer_read_only_error(correlation_message_id)
        if command_handler is None:
            return _transport_unavailable_error(correlation_message_id)
        entry = command_history_entry_from_payload(payload)
        if entry is None:
            return protocol_message(
                "response.error",
                {
                    "error_code": "invalid_command",
                    "error_message": "Replay commands must include a serialized history entry.",
                    "recommended_action": "Send raw_command, command_name, arguments, and timestamp.",
                    "retryable": True,
                },
                correlation_message_id=correlation_message_id,
            )
        if message_type == "command.toggle_replay_default_haul":
            try:
                command_handler.toggle_replay_default_haul(entry)
            except Exception as exc:
                return _command_execution_failed_error(exc, correlation_message_id)
            return protocol_message(
                "response.success",
                {"accepted": True, "message_text": "Default haul updated."},
                correlation_message_id=correlation_message_id,
            )
        edit_value = payload.get("edit", False)
        skip_delay_value = payload.get("skip_delay", False)
        try:
            command_handler.replay_history_entry(
                entry,
                edit=bool(edit_value),
                skip_delay=bool(skip_delay_value),
            )
        except Exception as exc:
            return _command_execution_failed_error(exc, correlation_message_id)
        return protocol_message(
            "response.success",
            {"accepted": True, "message_text": "Replay entry accepted."},
            correlation_message_id=correlation_message_id,
        )

    if message_type == "command.cancel_active_routine":
        if client_role != "active_operator":
            return protocol_message(
                "response.error",
                {
                    "error_code": "observer_read_only",
                    "error_message": "Observer clients cannot cancel operator routines.",
                    "recommended_action": "Use an active operator session to control routines.",
                    "retryable": False,
                },
                correlation_message_id=correlation_message_id,
            )
        if command_handler is None:
            return protocol_message(
                "response.error",
                {
                    "error_code": "active_operator_transport_unavailable",
                    "error_message": "Remote active-operator routine control is not available yet.",
                    "recommended_action": "Keep using embedded local mode for operator routine control until promotion lands.",
                    "retryable": False,
                },
                correlation_message_id=correlation_message_id,
            )
        try:
            command_handler.cancel_active_routine()
        except Exception as exc:
            return protocol_message(
                "response.error",
                {
                    "error_code": "command_execution_failed",
                    "error_message": str(exc) or "Remote routine cancellation failed.",
                    "recommended_action": "Check the server activity log, then try again.",
                    "retryable": True,
                },
                correlation_message_id=correlation_message_id,
            )
        return protocol_message(
            "response.success",
            {
                "accepted": True,
                "message_text": "Routine cancellation requested.",
            },
            correlation_message_id=correlation_message_id,
        )
    return protocol_message(
        "response.error",
        {
            "error_code": "unsupported_message_type",
            "error_message": f"Unsupported message type: {message_type}",
            "recommended_action": "Use a supported command or upgrade the client.",
            "retryable": False,
        },
        correlation_message_id=correlation_message_id,
    )


def _observer_read_only_error(correlation_message_id: str | None) -> dict[str, object]:
    return protocol_message(
        "response.error",
        {
            "error_code": "observer_read_only",
            "error_message": "Observer clients cannot issue operator commands.",
            "recommended_action": "Use an active operator session to run commands.",
            "retryable": False,
        },
        correlation_message_id=correlation_message_id,
    )


def _transport_unavailable_error(correlation_message_id: str | None) -> dict[str, object]:
    return protocol_message(
        "response.error",
        {
            "error_code": "active_operator_transport_unavailable",
            "error_message": "Remote active-operator command execution is not available yet.",
            "recommended_action": "Keep using embedded local mode for operator commands until promotion lands.",
            "retryable": False,
        },
        correlation_message_id=correlation_message_id,
    )


def _command_execution_failed_error(
    exc: Exception,
    correlation_message_id: str | None,
) -> dict[str, object]:
    return protocol_message(
        "response.error",
        {
            "error_code": "command_execution_failed",
            "error_message": str(exc) or "Remote command execution failed.",
            "recommended_action": "Check the command and server activity log, then try again.",
            "retryable": True,
        },
        correlation_message_id=correlation_message_id,
    )
