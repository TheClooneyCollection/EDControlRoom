from __future__ import annotations

from dataclasses import asdict
from typing import Callable

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect

from edap.control_room.server.auth import ObserverServerAuth
from edap.control_room.server.broker import InMemoryObserverSessionBroker
from edap.control_room.server.messages import protocol_message


def build_observer_server_app(
    *,
    snapshot_provider: Callable[[], object],
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
        snapshot = broker.merge_snapshot(snapshot_provider())
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
        snapshot = broker.merge_snapshot(snapshot_provider())
        auth_description = auth.describe()
        return JSONResponse(
            {
                "capability_names": snapshot.server_status.capability_names,
                "supported_client_roles": ["observer"],
                "supported_message_types": [
                    "state.snapshot",
                    "event.connection_ready",
                    "event.activity_log_appended",
                    "event.announcement_emitted",
                ],
                "minimum_client_version": "1",
                "server_version": snapshot.server_status.server_version,
                "authentication_required": auth_description.authentication_required,
                "authentication_scheme": auth_description.authentication_scheme,
                "authentication_supported_transports": list(auth_description.supported_transports),
                "authentication_query_parameter_name": auth_description.query_parameter_name,
            }
        )

    async def snapshot(request):
        auth_failure = require_http_auth(request)
        if auth_failure is not None:
            return auth_failure
        return JSONResponse(asdict(broker.merge_snapshot(snapshot_provider())))

    async def session(websocket: WebSocket) -> None:
        if not auth.is_websocket_authorized(websocket):
            await websocket.close(code=4401, reason="authentication required")
            return
        client_name = websocket.query_params.get("client_name", "observer-client")
        await websocket.accept()
        observer = broker.register_observer(client_name)
        merged_snapshot = broker.merge_snapshot(snapshot_provider())
        try:
            await websocket.send_json(
                protocol_message(
                    "event.connection_ready",
                    {
                        "session_id": observer.session_id,
                        "server_name": merged_snapshot.server_status.server_name,
                        "server_version": merged_snapshot.server_status.server_version,
                        "client_role": "observer",
                        "capability_names": merged_snapshot.server_status.capability_names,
                    },
                )
            )
            await websocket.send_json(protocol_message("state.snapshot", asdict(merged_snapshot)))
            while True:
                message = await observer.queue.get()
                await websocket.send_json(protocol_message(message["message_type"], message["payload"]))
        except WebSocketDisconnect:
            pass
        finally:
            broker.unregister(observer.session_id)

    return Starlette(
        routes=[
            Route("/health", health),
            Route("/capabilities", capabilities),
            Route("/snapshot", snapshot),
            WebSocketRoute("/session", session),
        ]
    )
