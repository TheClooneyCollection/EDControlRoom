from __future__ import annotations

import asyncio
from dataclasses import asdict, replace
import json
from pathlib import Path
from typing import Any, Callable

from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect

from edap.control_room.server.auth import ObserverServerAuth
from edap.control_room.server.broker import InMemoryObserverSessionBroker
from edap.control_room.server.commands import ObserverSessionCommandHandler, trade_route_from_payload
from edap.routing.web import (
    available_fixtures,
    build_live_comparison,
    comparison_to_payload,
    load_fixture_comparison,
)
from edap.haul_search_config import (
    GENERATED_HAUL_SEARCH_FIELDS,
    HaulSearchConfigError,
    save_haul_search_config,
)
from edap.inara.trade_routes import (
    TradeRoute,
    TradeRouteSearchResult,
    search_trade_routes,
)
from edap.control_room.protocol import (
    SUPPORTED_COMMAND_MESSAGE_TYPES,
    SUPPORTED_EVENT_MESSAGE_TYPES,
    SUPPORTED_MESSAGE_TYPES,
    SUPPORTED_RESPONSE_MESSAGE_TYPES,
    build_remote_observer_capabilities_payload,
    hydrate_message,
)
from edap.control_room.routine_stop import normalize_routine_stop_mode
from edap.control_room.server.messages import protocol_message

MESSAGE_SCHEMA_URL_PATH = "/schema/control_room_message.json"
BROWSER_PROBE_URL_PATH = "/browser-probe"
HAUL_WEB_ENTRY_URL_PATH = "/"
HAUL_WEB_URL_PATH = "/haul"
MULTI_HAUL_WEB_URL_PATH = "/multi-haul"
HAUL_WEB_ASSET_URL_PATH = "/assets/{asset_name:str}"
_MESSAGE_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3] / "docs" / "schemas" / "control_room_message.schema.json"
)
_BROWSER_PROBE_PATH = (
    Path(__file__).resolve().parents[3] / "tools" / "scratch" / "control_room_remote_browser.html"
)
_HAUL_WEB_PATH = Path(__file__).resolve().parents[3] / "web" / "haul-v1.html"
_MULTI_HAUL_WEB_PATH = Path(__file__).resolve().parents[3] / "web" / "multi-haul.html"
_HAUL_WEB_ASSET_DIR = Path(__file__).resolve().parents[3] / "web"
CONTROL_ROOM_MESSAGE_SCHEMA = json.loads(_MESSAGE_SCHEMA_PATH.read_text(encoding="utf-8"))
CONTROL_ROOM_BROWSER_PROBE_HTML = _BROWSER_PROBE_PATH.read_text(encoding="utf-8")
_HAUL_WEB_CONFIG_SENTINEL = "window.EDCR_WEB_CONFIG = {};"


def _render_haul_web_html(*, web_config: dict[str, Any] | None = None, web_default_access_token: str = "") -> str:
    return _render_web_html(
        _HAUL_WEB_PATH,
        web_config=web_config,
        web_default_access_token=web_default_access_token,
    )


def _render_multi_haul_web_html(
    *,
    web_config: dict[str, Any] | None = None,
    web_default_access_token: str = "",
) -> str:
    return _render_web_html(
        _MULTI_HAUL_WEB_PATH,
        web_config=web_config,
        web_default_access_token=web_default_access_token,
    )


def _render_web_html(
    path: Path,
    *,
    web_config: dict[str, Any] | None = None,
    web_default_access_token: str = "",
) -> str:
    resolved_config = dict(web_config or {})
    if web_default_access_token and "defaultAccessToken" not in resolved_config:
        resolved_config["defaultAccessToken"] = web_default_access_token
    html = path.read_text(encoding="utf-8").replace(
        _HAUL_WEB_CONFIG_SENTINEL,
        f"window.EDCR_WEB_CONFIG = {json.dumps(resolved_config, sort_keys=True)};",
    )
    return html


def _haul_web_config(
    data: object,
    *,
    auth: ObserverServerAuth,
    request: Request,
    web_default_access_token: str,
) -> dict[str, Any]:
    auth_description = auth.describe()
    server_status = getattr(data, "server_status", None)
    session = getattr(data, "session", None)
    return {
        "authQueryParameterName": auth_description.query_parameter_name or "access_token",
        "clientName": "web-haul",
        "defaultAccessToken": web_default_access_token,
        "hostLabel": request.url.netloc,
        "serverName": getattr(server_status, "server_name", "ED Control Room"),
        "serverVersion": getattr(server_status, "server_version", ""),
        "runtimePlatform": getattr(server_status, "runtime_platform", ""),
        "journalStatus": getattr(server_status, "journal_source_status", ""),
        "bindingsStatus": getattr(server_status, "bindings_source_status", ""),
        "inputTargetSummary": getattr(server_status, "input_target_summary", "foreground window"),
        "sessionRole": getattr(session, "client_role", "observer"),
        "webDefaults": dict(getattr(server_status, "web_form_defaults", {}) or {}),
    }


def build_observer_server_app(
    *,
    data_provider: Callable[[], object],
    command_handler: ObserverSessionCommandHandler | None,
    broker: InMemoryObserverSessionBroker,
    auth: ObserverServerAuth,
    web_default_access_token: str = "",
    journal_dir: Path | None = None,
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
        data = data_provider()
        auth_description = auth.describe()
        return JSONResponse(
            {
                "status": "ok",
                "server_name": data.server_status.server_name,
                "server_version": data.server_status.server_version,
                "observer_mode": True,
                "authentication_required": auth_description.authentication_required,
            }
        )

    async def capabilities(request):
        auth_failure = require_http_auth(request)
        if auth_failure is not None:
            return auth_failure
        data = data_provider()
        auth_description = auth.describe()
        return JSONResponse(
            build_remote_observer_capabilities_payload(
                capability_names=data.server_status.capability_names,
                server_version=data.server_status.server_version,
                authentication_required=auth_description.authentication_required,
                authentication_scheme=auth_description.authentication_scheme,
                authentication_supported_transports=auth_description.supported_transports,
                authentication_query_parameter_name=auth_description.query_parameter_name,
                message_schema_url=MESSAGE_SCHEMA_URL_PATH,
                browser_probe_url=BROWSER_PROBE_URL_PATH,
            )
        )

    async def hydrate(request):
        auth_failure = require_http_auth(request)
        if auth_failure is not None:
            return auth_failure
        return JSONResponse(hydrate_message(_server_hydrate_data(data_provider(), broker=broker)))

    async def message_schema(request):
        return JSONResponse(CONTROL_ROOM_MESSAGE_SCHEMA)

    async def browser_probe(request):
        return HTMLResponse(CONTROL_ROOM_BROWSER_PROBE_HTML)

    async def haul_web(request):
        data = data_provider()
        return HTMLResponse(
            _render_haul_web_html(
                web_config=_haul_web_config(
                    data,
                    auth=auth,
                    request=request,
                    web_default_access_token=web_default_access_token,
                )
            ),
            headers={"Cache-Control": "no-store"},
        )

    async def multi_haul_web(request):
        data = data_provider()
        return HTMLResponse(
            _render_multi_haul_web_html(
                web_config=_haul_web_config(
                    data,
                    auth=auth,
                    request=request,
                    web_default_access_token=web_default_access_token,
                )
            ),
            headers={"Cache-Control": "no-store"},
        )

    async def haul_web_asset(request):
        asset_name = request.path_params["asset_name"]
        allowed_assets = {
            "haul-ui.css": "text/css; charset=utf-8",
            "haul-ui.js": "text/javascript; charset=utf-8",
            "multi-haul.js": "text/javascript; charset=utf-8",
            "route-compare.js": "text/javascript; charset=utf-8",
        }
        media_type = allowed_assets.get(asset_name)
        if media_type is None:
            return JSONResponse({"detail": "not found"}, status_code=404)
        asset_path = _HAUL_WEB_ASSET_DIR / asset_name
        if not asset_path.is_file():
            return JSONResponse({"detail": "not found"}, status_code=404)
        return Response(
            asset_path.read_text(encoding="utf-8"),
            media_type=media_type,
            headers={"Cache-Control": "no-store"},
        )

    async def route_compare(request: Request) -> JSONResponse:
        auth_failure = require_http_auth(request)
        if auth_failure is not None:
            return auth_failure
        params = request.query_params
        fixture_name = params.get("fixture")
        if fixture_name:
            try:
                comparison = await asyncio.to_thread(load_fixture_comparison, fixture_name)
            except ValueError as exc:
                return JSONResponse(
                    {"detail": str(exc), "available_fixtures": list(available_fixtures())},
                    status_code=400,
                )
            return JSONResponse(comparison_to_payload(comparison))

        source_system = (params.get("from") or "").strip()
        destination_system = (params.get("to") or "").strip()
        range_raw = params.get("range")
        if not source_system or not destination_system or not range_raw:
            return JSONResponse(
                {"detail": "from, to, and range are required (or pass fixture=<name>)"},
                status_code=400,
            )
        if journal_dir is None:
            return JSONResponse(
                {"detail": "server has no journal_dir configured; live comparison unavailable"},
                status_code=503,
            )
        try:
            range_ly = float(range_raw)
            efficiency = int(params.get("efficiency", "60"))
            supercharge_multiplier = int(params.get("supercharge_multiplier", "4"))
        except ValueError as exc:
            return JSONResponse({"detail": f"invalid numeric parameter: {exc}"}, status_code=400)
        try:
            comparison = await asyncio.to_thread(
                build_live_comparison,
                journal_dir=journal_dir,
                source_system=source_system,
                destination_system=destination_system,
                range_ly=range_ly,
                efficiency=efficiency,
                supercharge_multiplier=supercharge_multiplier,
            )
        except FileNotFoundError:
            return JSONResponse({"detail": "NavRoute.json not found; plot a route in game first"}, status_code=404)
        except Exception as exc:
            return JSONResponse({"detail": f"route comparison failed: {exc}"}, status_code=502)
        return JSONResponse(comparison_to_payload(comparison))

    async def session(websocket: WebSocket) -> None:
        if not auth.is_websocket_authorized(websocket):
            await websocket.close(code=4401, reason="authentication required")
            return
        client_name = websocket.query_params.get("client_name", "observer-client")
        await websocket.accept()
        observer = broker.register_observer(client_name)
        data = data_provider()
        try:
            await websocket.send_json(
                protocol_message(
                    "event.connection_ready",
                    {
                        "session_id": observer.session_id,
                        "server_name": data.server_status.server_name,
                        "server_version": data.server_status.server_version,
                        "client_role": broker.current_session_role(observer.session_id),
                        "capability_names": data.server_status.capability_names,
                    },
                )
            )
            await websocket.send_json(hydrate_message(_server_hydrate_data(data_provider(), broker=broker)))
            sender = asyncio.create_task(_send_session_messages(websocket, observer))
            receiver = asyncio.create_task(
                _receive_session_messages(
                    websocket,
                    observer=observer,
                    command_handler=command_handler,
                    broker=broker,
                    data_provider=data_provider,
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

    app = Starlette(
        routes=[
            Route("/health", health),
            Route("/capabilities", capabilities),
            Route("/hydrate", hydrate),
            Route(MESSAGE_SCHEMA_URL_PATH, message_schema),
            Route(BROWSER_PROBE_URL_PATH, browser_probe),
            Route(HAUL_WEB_ENTRY_URL_PATH, haul_web),
            Route(HAUL_WEB_URL_PATH, haul_web),
            Route(MULTI_HAUL_WEB_URL_PATH, multi_haul_web),
            Route("/api/route-compare", route_compare),
            Route(HAUL_WEB_ASSET_URL_PATH, haul_web_asset),
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


def _response_error(
    error_code: str,
    error_message: str,
    *,
    retryable: bool,
    correlation_message_id: str | None,
) -> dict[str, object]:
    return protocol_message(
        "response.error",
        {
            "error_code": error_code,
            "error_message": error_message,
            "retryable": retryable,
        },
        correlation_message_id=correlation_message_id,
    )


def _server_hydrate_data(
    data: object,
    *,
    broker: InMemoryObserverSessionBroker,
) -> object:
    selected_trade_route = (
        broker.server_state.selected_trade_route()
        or getattr(data, "selected_trade_route", None)
    )
    running_trade_route = (
        broker.server_state.running_trade_route()
        or getattr(data, "running_trade_route", None)
    )
    return replace(
        data,
        selected_trade_route=selected_trade_route,
        running_trade_route=running_trade_route,
    )


def _publish_route_hydrate(
    *,
    broker: InMemoryObserverSessionBroker,
    data_provider: Callable[[], object] | None,
) -> None:
    if data_provider is None:
        return
    broker.publish_data_message(
        hydrate_message(_server_hydrate_data(data_provider(), broker=broker))
    )


def _persist_route_state(
    command_handler: ObserverSessionCommandHandler | None,
    *,
    selected_trade_route: TradeRoute | None = None,
    running_trade_route: TradeRoute | None = None,
) -> None:
    if command_handler is None:
        return
    persist = getattr(command_handler, "persist_trade_route_state", None)
    if callable(persist):
        persist(
            selected_trade_route=selected_trade_route,
            running_trade_route=running_trade_route,
        )


async def _handle_search_haul_routes_message_async(
    message: dict[str, object],
    *,
    client_role: str,
    data_provider: Callable[[], object] | None,
) -> dict[str, object]:
    message_id_value = message.get("message_id")
    correlation_message_id = message_id_value if isinstance(message_id_value, str) else None
    payload_value = message.get("payload", {})
    payload = payload_value if isinstance(payload_value, dict) else {}
    if data_provider is None:
        return _transport_unavailable_error(correlation_message_id)
    data = data_provider()
    system_name = _payload_string(payload, "system_name") or _payload_string(payload, "origin")
    if not system_name:
        system_name = (getattr(data.ship, "system", "") or "").strip()
    if not system_name:
        return _response_error(
            "invalid_search",
            "Haul search needs an origin system.",
            retryable=True,
            correlation_message_id=correlation_message_id,
        )
    query_params = _haul_search_query_params(payload, data=data)
    await asyncio.to_thread(_save_haul_search_defaults, query_params)
    destination_filter = (
        _payload_string(payload, "destination")
        or _payload_string(payload, "destination_filter")
        or ""
    )
    try:
        result = await asyncio.to_thread(
            search_trade_routes,
            system_name,
            query_params=query_params,
        )
    except Exception as exc:
        return _response_error(
            "haul_search_failed",
            str(exc) or "Failed to search haul routes.",
            retryable=True,
            correlation_message_id=correlation_message_id,
        )
    routes = list(result.routes)
    unfiltered_count = len(routes)
    if destination_filter:
        routes = [
            route
            for route in routes
            if _route_matches_destination(route, destination_filter)
        ]
    return protocol_message(
        "response.success",
        {
            "accepted": True,
            "message_text": "Haul search complete.",
            "result": _haul_search_response(
                result,
                routes=routes,
                unfiltered_count=unfiltered_count,
            ),
        },
        correlation_message_id=correlation_message_id,
    )


def _payload_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if value is None:
        return ""
    return str(value).strip()


def _haul_search_query_params(
    payload: dict[str, Any],
    *,
    data: object,
) -> dict[str, str]:
    ship = getattr(data, "ship", None)
    cargo_capacity = _payload_string(payload, "cargo_capacity")
    if not cargo_capacity and ship is not None:
        cargo_capacity_value = getattr(ship, "cargo_capacity", 0)
        if cargo_capacity_value:
            cargo_capacity = str(cargo_capacity_value)

    order_by = _payload_string(payload, "order_by")
    if not order_by:
        metric = _payload_string(payload, "metric").lower()
        order_by = "best_profit" if "trip" in metric else "best_profit_per_hour_estimate"

    params: dict[str, str] = {
        "use_surface_stations": "no",
    }
    if cargo_capacity:
        params["cargo_capacity"] = cargo_capacity
    route_distance = _numberish_string(_payload_string(payload, "max_route_distance_ly"))
    if route_distance:
        params["max_route_distance_ly"] = route_distance
    station_distance = _payload_string(payload, "max_station_distance_ls")
    if station_distance:
        params["max_station_distance_ls"] = _numberish_string(station_distance) or "any"
    if order_by:
        params["order_by"] = order_by
    return params


def _numberish_string(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        return ""
    lowered = stripped.lower()
    if lowered == "any":
        return "any"
    first = stripped.split()[0].replace(",", "")
    return first if first else stripped


def _save_haul_search_defaults(query_params: dict[str, str]) -> None:
    try:
        save_haul_search_config(query_params, exclude=GENERATED_HAUL_SEARCH_FIELDS)
    except (OSError, HaulSearchConfigError):
        return None


def _route_matches_destination(route: TradeRoute, destination_filter: str) -> bool:
    needle = destination_filter.strip().lower()
    if not needle:
        return True
    haystack = " ".join(
        value
        for value in (
            route.to_station,
            route.to_system,
        )
        if value
    ).lower()
    return needle in haystack


def _haul_search_response(
    result: TradeRouteSearchResult,
    *,
    routes: list[TradeRoute],
    unfiltered_count: int,
) -> dict[str, Any]:
    return {
        "system_name": result.system_name,
        "query_url": result.query_url,
        "searched_at": result.searched_at,
        "route_count": len(routes),
        "unfiltered_route_count": unfiltered_count,
        "station_carrier_only": True,
        "routes": [_trade_route_to_payload(route) for route in routes],
    }


def _trade_route_to_payload(route: TradeRoute) -> dict[str, Any]:
    return asdict(route)


async def _send_session_messages(websocket: WebSocket, observer) -> None:
    while True:
        message = await observer.queue.get()
        if "schema" in message:
            await websocket.send_json(message)
        else:
            await websocket.send_json(protocol_message(message["message_type"], message["payload"]))


async def _receive_session_messages(
    websocket: WebSocket,
    *,
    observer,
    command_handler: ObserverSessionCommandHandler | None,
    broker: InMemoryObserverSessionBroker,
    data_provider: Callable[[], object],
) -> None:
    while True:
        message = await websocket.receive_json()
        response = await _handle_session_message_async(
            message,
            session_id=observer.session_id,
            client_role=broker.current_session_role(observer.session_id),
            command_handler=command_handler,
            broker=broker,
            data_provider=data_provider,
        )
        if response is None:
            continue
        await websocket.send_json(response)


async def _handle_session_message_async(
    message: dict[str, object],
    *,
    session_id: str,
    client_role: str,
    command_handler: ObserverSessionCommandHandler | None,
    broker: InMemoryObserverSessionBroker,
    data_provider: Callable[[], object] | None = None,
) -> dict[str, object] | None:
    if message.get("message_type") == "command.search_haul_routes":
        return await _handle_search_haul_routes_message_async(
            message,
            client_role=client_role,
            data_provider=data_provider,
        )
    return _handle_session_message(
        message,
        session_id=session_id,
        client_role=client_role,
        command_handler=command_handler,
        broker=broker,
        data_provider=data_provider,
    )


def _handle_session_message(
    message: dict[str, object],
    *,
    session_id: str,
    client_role: str,
    command_handler: ObserverSessionCommandHandler | None,
    broker: InMemoryObserverSessionBroker,
    data_provider: Callable[[], object] | None = None,
) -> dict[str, object] | None:
    message_type = str(message.get("message_type", ""))
    message_id = message.get("message_id")
    correlation_message_id = str(message_id) if message_id is not None else None
    payload_value = message.get("payload", {})
    payload = payload_value if isinstance(payload_value, dict) else {}

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

    if message_type == "command.dispatch_destination":
        if command_handler is None:
            return _transport_unavailable_error(correlation_message_id)
        destination = payload.get("destination")
        galaxy_map_settle = payload.get("galaxy_map_settle")
        raw_command_value = payload.get("raw_command")
        raw_command = raw_command_value if isinstance(raw_command_value, str) else None
        if not isinstance(destination, str) or not destination.strip():
            return protocol_message(
                "response.error",
                {
                    "error_code": "invalid_command",
                    "error_message": "Destination dispatch commands must include a destination string.",
                    "recommended_action": "Send a non-empty destination value.",
                    "retryable": True,
                },
                correlation_message_id=correlation_message_id,
            )
        if not isinstance(galaxy_map_settle, (int, float)):
            return protocol_message(
                "response.error",
                {
                    "error_code": "invalid_command",
                    "error_message": "Destination dispatch commands must include a numeric galaxy_map_settle.",
                    "recommended_action": "Send a numeric galaxy_map_settle value.",
                    "retryable": True,
                },
                correlation_message_id=correlation_message_id,
            )
        try:
            skip_delay_value = payload.get("skip_delay")
            skip_delay = bool(skip_delay_value) if isinstance(skip_delay_value, bool) else False
            command_handler.dispatch_destination(
                destination.strip(),
                float(galaxy_map_settle),
                skip_delay=skip_delay,
                raw_command=raw_command,
            )
        except Exception as exc:
            return _command_execution_failed_error(exc, correlation_message_id)
        return protocol_message(
            "response.success",
            {
                "accepted": True,
                "message_text": "Destination routine accepted.",
                "result": {"destination": destination.strip()},
            },
            correlation_message_id=correlation_message_id,
        )

    if message_type == "command.dispatch_travel":
        if command_handler is None:
            return _transport_unavailable_error(correlation_message_id)
        system = payload.get("system")
        station = payload.get("station", "")
        raw_command_value = payload.get("raw_command")
        raw_command = raw_command_value if isinstance(raw_command_value, str) else None
        if not isinstance(system, str) or not system.strip():
            return protocol_message(
                "response.error",
                {
                    "error_code": "invalid_command",
                    "error_message": "Travel dispatch commands must include a system string.",
                    "recommended_action": "Send a non-empty destination system value.",
                    "retryable": True,
                },
                correlation_message_id=correlation_message_id,
            )
        if not isinstance(station, str):
            return protocol_message(
                "response.error",
                {
                    "error_code": "invalid_command",
                    "error_message": "Travel dispatch commands must include a station string when station is present.",
                    "recommended_action": "Send a station string or omit it for system-only travel.",
                    "retryable": True,
                },
                correlation_message_id=correlation_message_id,
            )
        try:
            skip_delay_value = payload.get("skip_delay")
            skip_delay = bool(skip_delay_value) if isinstance(skip_delay_value, bool) else False
            on_land_value = payload.get("on_land")
            on_land = bool(on_land_value) if isinstance(on_land_value, bool) else False
            command_handler.dispatch_travel(
                system=system.strip(),
                station=station.strip(),
                on_land=on_land,
                skip_delay=skip_delay,
                raw_command=raw_command,
            )
        except Exception as exc:
            return _command_execution_failed_error(exc, correlation_message_id)
        return protocol_message(
            "response.success",
            {
                "accepted": True,
                "message_text": "Travel routine accepted.",
                "result": {
                    "system": system.strip(),
                    "station": station.strip(),
                },
            },
            correlation_message_id=correlation_message_id,
        )

    if message_type == "command.dispatch_haul_loop":
        if command_handler is None:
            return _transport_unavailable_error(correlation_message_id)
        params_value = payload.get("params", {})
        if not isinstance(params_value, dict):
            return protocol_message(
                "response.error",
                {
                    "error_code": "invalid_command",
                    "error_message": "Haul dispatch commands must include a params mapping.",
                    "recommended_action": "Send string haul params as a JSON object.",
                    "retryable": True,
                },
                correlation_message_id=correlation_message_id,
            )
        raw_command_value = payload.get("raw_command")
        raw_command = raw_command_value if isinstance(raw_command_value, str) else None
        trade_route = trade_route_from_payload(payload.get("trade_route"))
        params_for_dispatch = {str(key): str(value) for key, value in params_value.items()}
        if (
            trade_route is not None
            and trade_route.profit_per_trip
            and not params_for_dispatch.get("route_profit_per_trip")
        ):
            params_for_dispatch["route_profit_per_trip"] = trade_route.profit_per_trip
        try:
            skip_delay_value = payload.get("skip_delay")
            skip_delay = bool(skip_delay_value) if isinstance(skip_delay_value, bool) else False
            command_handler.dispatch_haul_loop(
                params=params_for_dispatch,
                skip_delay=skip_delay,
                raw_command=raw_command,
            )
        except Exception as exc:
            return _command_execution_failed_error(exc, correlation_message_id)
        if trade_route is not None:
            broker.server_state.set_selected_trade_route(trade_route)
            broker.server_state.set_running_trade_route(trade_route)
            _persist_route_state(
                command_handler,
                selected_trade_route=trade_route,
                running_trade_route=trade_route,
            )
            _publish_route_hydrate(broker=broker, data_provider=data_provider)
        return protocol_message(
            "response.success",
            {
                "accepted": True,
                "message_text": "Haul routine accepted.",
            },
            correlation_message_id=correlation_message_id,
        )

    if message_type == "command.select_trade_route":
        trade_route = trade_route_from_payload(payload.get("route"))
        if trade_route is None:
            return protocol_message(
                "response.error",
                {
                    "error_code": "invalid_command",
                    "error_message": "Trade-route selection commands must include a valid route object.",
                    "recommended_action": "Send a route returned by command.search_haul_routes.",
                    "retryable": True,
                },
                correlation_message_id=correlation_message_id,
            )
        broker.server_state.set_selected_trade_route(trade_route)
        _persist_route_state(
            command_handler,
            selected_trade_route=trade_route,
        )
        _publish_route_hydrate(broker=broker, data_provider=data_provider)
        return protocol_message(
            "response.success",
            {
                "accepted": True,
                "message_text": "Trade route selection stored.",
                "result": {"route": _trade_route_to_payload(trade_route)},
            },
            correlation_message_id=correlation_message_id,
        )

    if message_type == "command.search_haul_routes":
        if data_provider is None:
            return _transport_unavailable_error(correlation_message_id)
        data = data_provider()
        system_name = _payload_string(payload, "system_name") or _payload_string(payload, "origin")
        if not system_name:
            system_name = (getattr(data.ship, "system", "") or "").strip()
        if not system_name:
            return _response_error(
                "invalid_search",
                "Haul search needs an origin system.",
                retryable=True,
                correlation_message_id=correlation_message_id,
            )
        query_params = _haul_search_query_params(payload, data=data)
        _save_haul_search_defaults(query_params)
        destination_filter = (
            _payload_string(payload, "destination")
            or _payload_string(payload, "destination_filter")
            or ""
        )
        try:
            result = search_trade_routes(
                system_name,
                query_params=query_params,
            )
        except Exception as exc:
            return _response_error(
                "haul_search_failed",
                str(exc) or "Failed to search haul routes.",
                retryable=True,
                correlation_message_id=correlation_message_id,
            )
        routes = list(result.routes)
        unfiltered_count = len(routes)
        if destination_filter:
            routes = [
                route
                for route in routes
                if _route_matches_destination(route, destination_filter)
            ]
        return protocol_message(
            "response.success",
            {
                "accepted": True,
                "message_text": "Haul search complete.",
                "result": _haul_search_response(
                    result,
                    routes=routes,
                    unfiltered_count=unfiltered_count,
                ),
            },
            correlation_message_id=correlation_message_id,
        )

    if message_type == "command.cancel_active_routine":
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
        stop_mode = normalize_routine_stop_mode(payload.get("mode"))
        try:
            command_handler.cancel_active_routine(stop_mode=stop_mode)
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
                "message_text": (
                    "Routine stop-after-run requested."
                    if stop_mode == "after_run"
                    else "Routine cancellation requested."
                ),
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
