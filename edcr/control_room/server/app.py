from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, replace
from datetime import datetime
import json
import logging
import math
from pathlib import Path
import sqlite3
import threading
import time
from types import SimpleNamespace
from typing import Any, Awaitable, Callable, Mapping

import httpx

logger = logging.getLogger(__name__)

from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect

from edcr.eddn.route_query import (
    RouteQueryError,
    laden_jump_range,
    parse_route_query,
    resolve_route_params,
    run_route_query,
)
from edcr.config import TIME_MODEL_SOURCES, ConfigError, save_time_model
from edcr.eddn.routes import TimeModel
from edcr.trip_time_fit import FitShip, TripTimeModels, model_from_payload, parse_fit_ship
from edcr.haul_history import load_runs, parse_window, summarize
from edcr.journal_trade_ledger import journal_trade_ledger
from edcr.market_compare import compare_markets
from edcr.hub.history import ALL, filter_runs, history_options, parse_node_filter, parse_ship_filter
from edcr.hub.nodes import HubLinkSession, HubSide, RequestHandler
from edcr.hub.peer import PeerLink, hub_unreachable_detail, with_hub_source
from edcr.hub.relay import NODE_ACTIONS, NODE_READS, NodeOffline, node_state, relay_error
from edcr.hub.protocol import (
    PEER_LINK_PATH,
    REQUEST_CARRIER_NAMES,
    REQUEST_EDDN_ROUTES,
    REQUEST_EDDN_STATUS,
    REQUEST_HAUL_SEARCH,
    REQUEST_HAUL_STATS,
    REQUEST_MEASURED,
    REQUEST_STATION_FACTS,
    REQUEST_TIME_MODEL,
    HubUnreachable,
    LinkReply,
)
from edcr.recent_markets import (
    MarketSnapshot,
    load_recent_markets,
    market_items,
)
from edcr.trade_trip import (
    FactLookup, StationFacts, StationName, estimate_trip, gather_facts, measured_route, store_lookup,
)
from edcr.platform.local_time import SystemLocalTimezone
from edcr.control_room.server.auth import ObserverServerAuth, SharedAccessTokenAuth
from edcr.control_room.server.broker import InMemoryObserverSessionBroker
from edcr.control_room.server.commands import ObserverSessionCommandHandler, trade_route_from_payload
from edcr.routing.comparison import RouteComparison
from edcr.routing.route_cache import RouteRequestKey
from edcr.routing.types import SpanshMetadata
from edcr.routing.web import (
    available_fixtures,
    build_live_comparison,
    comparison_to_payload,
    load_fixture_comparison,
    route_payload,
)
from edcr.spansh_router import plot_route
from edcr.control_room.protocol import build_announcement_event
from edcr.tts import AnnouncementId
from edcr.haul_search_config import (
    GENERATED_HAUL_SEARCH_FIELDS,
    HaulSearchConfigError,
    load_haul_search_config,
    save_haul_search_config,
)
from edcr.inara.trade_routes import (
    TradeRoute,
    TradeRouteSearchResult,
    parse_surface_stations,
    search_trade_routes,
)
from edcr.control_room.protocol import (
    ACCESS_TOKEN_QUERY_PARAMETER,
    SUPPORTED_COMMAND_MESSAGE_TYPES,
    SUPPORTED_EVENT_MESSAGE_TYPES,
    SUPPORTED_MESSAGE_TYPES,
    SUPPORTED_RESPONSE_MESSAGE_TYPES,
    build_remote_observer_capabilities_payload,
    hydrate_message,
)
from edcr.control_room.routine_stop import normalize_routine_stop_mode
from edcr.control_room.server.messages import protocol_message

MESSAGE_SCHEMA_URL_PATH = "/schema/control_room_message.json"
BROWSER_PROBE_URL_PATH = "/browser-probe"
HAUL_WEB_ENTRY_URL_PATH = "/"
HAUL_WEB_URL_PATH = "/haul"
MULTI_HAUL_WEB_URL_PATH = "/multi-haul"
CONTROLS_WEB_URL_PATH = "/controls"
MARKETS_WEB_URL_PATH = "/markets"
ROUTES_WEB_URL_PATH = "/routes"
TRAVEL_WEB_URL_PATH = "/travel"
CONFIG_WEB_URL_PATH = "/config"
HAUL_WEB_ASSET_URL_PATH = "/assets/{asset_name:str}"
_MESSAGE_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3] / "docs" / "schemas" / "control_room_message.schema.json"
)
_BROWSER_PROBE_PATH = (
    Path(__file__).resolve().parents[3] / "tools" / "scratch" / "control_room_remote_browser.html"
)
_HAUL_WEB_PATH = Path(__file__).resolve().parents[3] / "web" / "haul-v1.html"
_MULTI_HAUL_WEB_PATH = Path(__file__).resolve().parents[3] / "web" / "multi-haul.html"
_CONTROLS_WEB_PATH = Path(__file__).resolve().parents[3] / "web" / "controls.html"
_MARKETS_WEB_PATH = Path(__file__).resolve().parents[3] / "web" / "markets.html"
_ROUTES_WEB_PATH = Path(__file__).resolve().parents[3] / "web" / "routes.html"
_TRAVEL_WEB_PATH = Path(__file__).resolve().parents[3] / "web" / "travel.html"
_CONFIG_WEB_PATH = Path(__file__).resolve().parents[3] / "web" / "config.html"
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


def _render_controls_web_html(
    *,
    web_config: dict[str, Any] | None = None,
    web_default_access_token: str = "",
) -> str:
    return _render_web_html(
        _CONTROLS_WEB_PATH,
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
        "serverCommit": getattr(server_status, "server_commit", ""),
        "runtimePlatform": getattr(server_status, "runtime_platform", ""),
        "journalStatus": getattr(server_status, "journal_source_status", ""),
        "bindingsStatus": getattr(server_status, "bindings_source_status", ""),
        "inputTargetSummary": getattr(server_status, "input_target_summary", "foreground window"),
        "sessionRole": getattr(session, "client_role", "observer"),
        "webDefaults": dict(getattr(server_status, "web_form_defaults", {}) or {}),
    }


class NodeLoop:
    """One long-lived event loop for the work a hub page runs on this peer (session commands, actions, reads).

    A local page's handlers run on the server's loop, and a routine they start (a Textual thread worker)
    lives on that loop. A fresh `asyncio.run` per relayed command would instead wait, as it closes its
    loop, for that routine thread to end, holding the hub page's channel (and its stop) for the whole run.
    Started on first use, so a server no hub page drives never starts it.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

    def run(self, work: Awaitable[Any]) -> Any:
        """Run `work` on the loop and wait for its result; never call this on the loop itself."""
        return asyncio.run_coroutine_threadsafe(work, self._started()).result()

    def _started(self) -> asyncio.AbstractEventLoop:
        with self._lock:
            if self._loop is None:
                loop = asyncio.new_event_loop()
                threading.Thread(target=loop.run_forever, name="node-loop", daemon=True).start()
                self._loop = loop
            return self._loop


def build_observer_server_app(
    *,
    data_provider: Callable[[], object],
    command_handler: ObserverSessionCommandHandler | None,
    broker: InMemoryObserverSessionBroker,
    auth: ObserverServerAuth,
    web_default_access_token: str = "",
    journal_dir: Path | None = None,
    haul_runs_file: Path | None = None,
    recent_markets_file: Path | None = None,
    eddn_status: Callable[[], dict[str, Any]] | None = None,
    market_database_file: Path | None = None,
    # The trip time model: configured, or fitted per ship from the journal store. None keeps the defaults.
    time_models: TripTimeModels | None = None,
    # Where `POST /api/time-model` saves the trip time settings; None cannot save them.
    config_file: Path | None = None,
    ardent_lookup: FactLookup | None = None,
    # Peer role: the link to the hub, which answers searches, routes and station facts.
    peer_link: PeerLink | None = None,
    # Hub role: the nodes that said hello, where their outbox items go and the token they present.
    hub_side: HubSide | None = None,
    route_compare_navroute_wait_seconds: float = 6.0,
    route_compare_compare_retry_attempts: int = 3,
) -> Starlette:
    if time_models is None:
        time_models = TripTimeModels(configured=TimeModel(), source="config", fit_days=14.0, fit_ship="current",
                                     connect=None,
                                     clock=time.time)

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
                "server_commit": data.server_status.server_commit,
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

    async def controls_web(request):
        data = data_provider()
        return HTMLResponse(
            _render_controls_web_html(
                web_config=_haul_web_config(
                    data,
                    auth=auth,
                    request=request,
                    web_default_access_token=web_default_access_token,
                )
            ),
            headers={"Cache-Control": "no-store"},
        )

    async def markets_web(request):
        data = data_provider()
        return HTMLResponse(
            _render_web_html(
                _MARKETS_WEB_PATH,
                web_config=_haul_web_config(
                    data,
                    auth=auth,
                    request=request,
                    web_default_access_token=web_default_access_token,
                ),
            ),
            headers={"Cache-Control": "no-store"},
        )

    async def routes_web(request):
        data = data_provider()
        return HTMLResponse(
            _render_web_html(
                _ROUTES_WEB_PATH,
                web_config=_haul_web_config(
                    data,
                    auth=auth,
                    request=request,
                    web_default_access_token=web_default_access_token,
                ),
            ),
            headers={"Cache-Control": "no-store"},
        )

    async def config_web(request):
        data = data_provider()
        return HTMLResponse(
            _render_web_html(
                _CONFIG_WEB_PATH,
                web_config=_haul_web_config(
                    data,
                    auth=auth,
                    request=request,
                    web_default_access_token=web_default_access_token,
                ),
            ),
            headers={"Cache-Control": "no-store"},
        )

    async def travel_web(request):
        data = data_provider()
        return HTMLResponse(
            _render_web_html(
                _TRAVEL_WEB_PATH,
                web_config=_haul_web_config(
                    data,
                    auth=auth,
                    request=request,
                    web_default_access_token=web_default_access_token,
                ),
            ),
            headers={"Cache-Control": "no-store"},
        )

    async def haul_web_asset(request):
        asset_name = request.path_params["asset_name"]
        allowed_assets = {
            "haul-ui.css": "text/css; charset=utf-8",
            "haul-ui.js": "text/javascript; charset=utf-8",
            "multi-haul.js": "text/javascript; charset=utf-8",
            "controls.js": "text/javascript; charset=utf-8",
            "markets.js": "text/javascript; charset=utf-8",
            "routes.js": "text/javascript; charset=utf-8",
            "travel.js": "text/javascript; charset=utf-8",
            "config.js": "text/javascript; charset=utf-8",
            "nav.js": "text/javascript; charset=utf-8",
            "route-compare.js": "text/javascript; charset=utf-8",
            "active-route.js": "text/javascript; charset=utf-8",
            "speech.js": "text/javascript; charset=utf-8",
            "hub-status.js": "text/javascript; charset=utf-8",
            "hub-voice.js": "text/javascript; charset=utf-8",
            "activity-dock.js": "text/javascript; charset=utf-8",
            "favicon.png": "image/png",
            "apple-touch-icon.png": "image/png",
        }
        media_type = allowed_assets.get(asset_name)
        if media_type is None:
            return JSONResponse({"detail": "not found"}, status_code=404)
        asset_path = _HAUL_WEB_ASSET_DIR / asset_name
        if not asset_path.is_file():
            return JSONResponse({"detail": "not found"}, status_code=404)
        return Response(
            asset_path.read_bytes(),
            media_type=media_type,
            headers={"Cache-Control": "no-store"},
        )

    async def favicon(request):
        # Browsers ask for /favicon.ico before (or without) reading the page's icon link.
        return Response((_HAUL_WEB_ASSET_DIR / "favicon.png").read_bytes(), media_type="image/png")

    async def route_compare(params: Mapping[str, str]) -> JSONResponse:
        fixture_name = params.get("fixture")
        if fixture_name:
            try:
                comparison = await asyncio.to_thread(load_fixture_comparison, fixture_name)
            except ValueError as exc:
                return JSONResponse(
                    {"detail": str(exc), "available_fixtures": list(available_fixtures())},
                    status_code=400,
                )
            _publish_spansh_route_ready(broker, comparison)
            route_id = _cache_comparison_spansh_route(broker, comparison, range_ly=0.0)
            payload = comparison_to_payload(comparison)
            payload["route_id"] = route_id
            return JSONResponse(payload)

        source_system = (params.get("from") or "").strip()
        destination_system = (params.get("to") or "").strip()
        range_raw = params.get("range")
        if not source_system or not destination_system or not range_raw:
            return JSONResponse(
                {"detail": "from, to, and range are required (or pass fixture=<name>)"},
                status_code=400,
            )
        try:
            range_ly = float(range_raw)
            efficiency = int(params.get("efficiency", "60"))
            supercharge_multiplier = int(params.get("supercharge_multiplier", "4"))
        except ValueError as exc:
            return JSONResponse({"detail": f"invalid numeric parameter: {exc}"}, status_code=400)
        try:
            payload = await asyncio.to_thread(
                build_and_cache_live_comparison,
                broker=broker,
                journal_dir=journal_dir,
                source_system=source_system,
                destination_system=destination_system,
                range_ly=range_ly,
                efficiency=efficiency,
                supercharge_multiplier=supercharge_multiplier,
            )
        except RouteCompareError as exc:
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
        return JSONResponse(payload)

    async def route_compare_config(_params: Mapping[str, str]) -> JSONResponse:
        return JSONResponse(
            {
                "navroute_wait_seconds": route_compare_navroute_wait_seconds,
                "compare_retry_attempts": route_compare_compare_retry_attempts,
            }
        )

    # This server's own node: the hub's local node, or the peer itself; a standalone server has none.
    own_node = hub_side.registry.local if hub_side is not None else peer_link.hello if peer_link is not None else None

    def read_history() -> tuple[list[dict[str, Any]], int]:
        """Hub: every node's runs, tagged with their node. Standalone: this server's own file."""
        if hub_side is not None:
            return hub_side.history.rows()
        return load_runs(haul_runs_file) if haul_runs_file is not None else ([], 0)

    def answer_haul_stats(body: Any) -> LinkReply:
        """Haul history for a window, node and ship, from the history this server owns; peers ask it too."""
        if not isinstance(body, dict):
            return LinkReply(400, {"detail": "body must be a JSON object"})
        window = str(body.get("window") or "today")
        try:
            since, until, label = parse_window(window, datetime.now(SystemLocalTimezone()))
            node = parse_node_filter(str(body.get("node") or ""))
            ship = parse_ship_filter(str(body.get("ship") or ""))
        except ValueError as exc:
            return LinkReply(400, {"detail": str(exc)})
        try:
            rows, skipped = read_history()
        except (OSError, ValueError) as exc:
            return LinkReply(503, {"detail": f"Cannot read haul statistics: {exc}"})
        runs = summarize(filter_runs(rows, node=node, ship=ship), since, until, skipped_lines=skipped)
        return LinkReply(200, {
            "window": window, "label": label,
            "since": since.isoformat() if since is not None else None, "until": until.isoformat(),
            "node": node, "ship": ship if ship is not None else ALL,
            "runs": asdict(runs),
            **history_options(rows, own_node if hub_side is not None else None),
        })

    def own_journal(window: str) -> dict[str, Any] | None:
        """The trade ledger from this machine's own journals, or None without one."""
        since, until, _ = parse_window(window, datetime.now(SystemLocalTimezone()))
        ledger = journal_trade_ledger(journal_dir, since, until) if journal_dir is not None else None
        return asdict(ledger) if ledger is not None and ledger.available else None

    def with_journal(payload: dict[str, Any], window: str, node: str, viewed: str | None) -> dict[str, Any]:
        """The trade ledger of the node a page looks at (`viewed`, a peer, or this machine for None):
        shown for every node or that one only. A peer's ledger comes over the link."""
        if viewed is not None:
            assert relay is not None
            journal = None
            if node in {ALL, viewed}:
                try:
                    reply = relay.read(viewed, "/api/journal-ledger", {"window": window})
                except NodeOffline:
                    reply = LinkReply(502, None)
                journal = reply.body.get("journal") if reply.status == 200 and isinstance(reply.body, dict) else None
            return {**payload, "journal": journal, "journal_node": relay.name(viewed)}
        ours = node == ALL or (own_node is not None and node == own_node.node_id)
        return {
            **payload,
            "journal": own_journal(window) if ours else None,
            "journal_node": own_node.name if own_node is not None else None,
        }

    async def journal_ledger(params: Mapping[str, str]) -> JSONResponse:
        """This machine's journal ledger for a window: a hub page looking at this peer asks for it."""
        window = params.get("window", "today")
        try:
            return JSONResponse({"window": window, "journal": await asyncio.to_thread(own_journal, window)})
        except ValueError as exc:
            return JSONResponse({"detail": str(exc)}, status_code=400)
        except OSError as exc:
            return JSONResponse({"detail": f"Cannot read the journal ledger: {exc}"}, status_code=503)

    async def haul_stats_endpoint(request: Request) -> JSONResponse:
        auth_failure = require_http_auth(request)
        if auth_failure is not None:
            return auth_failure
        params = request.query_params
        body = {"window": params.get("window", "today"), "node": params.get("node", ALL),
                "ship": params.get("ship", ALL)}
        try:
            parse_window(body["window"], datetime.now(SystemLocalTimezone()))
            node = parse_node_filter(body["node"])
            parse_ship_filter(body["ship"])
        except ValueError as exc:
            return JSONResponse({"detail": str(exc)}, status_code=400)
        if peer_link is not None:
            # A peer owns no history to show: the hub has every node's runs, this one's included.
            try:
                reply = await asyncio.to_thread(peer_link.request, REQUEST_HAUL_STATS, body,
                                                timeout_s=peer_link.request_timeout_s)
            except HubUnreachable as exc:
                label = peer_link.hub_label
                return JSONResponse({"detail": hub_unreachable_detail(label, exc), "hub": label}, status_code=502)
            reply = LinkReply(reply.status, with_hub_source(reply.body, peer_link.hub_label))
        else:
            reply = await asyncio.to_thread(answer_haul_stats, body)
        if reply.status != 200 or not isinstance(reply.body, dict):
            return link_reply_response(reply)
        try:
            # `node` is the history filter; `view_node` is the node the page looks at (its ledger).
            viewed = viewed_node({"node": params.get("view_node", "")})
            return JSONResponse(await asyncio.to_thread(with_journal, reply.body, body["window"], node, viewed))
        except (OSError, ValueError) as exc:
            return JSONResponse({"detail": f"Cannot read haul statistics: {exc}"}, status_code=503)

    def read_recent_markets() -> tuple[MarketSnapshot, ...]:
        return load_recent_markets(recent_markets_file) if recent_markets_file is not None else ()

    def viewed_ship(params: Mapping[str, str]) -> Any:
        """The ship a page prices trips or fits trip time for: on a hub the picked node's, as it last
        reported it (so an offline node keeps its last ship), else this server's own."""
        node_id = viewed_node(params)
        reported = hub_side.registry.last_ship(node_id) if hub_side is not None and node_id is not None else None
        if reported is None:
            return getattr(data_provider(), "ship", None)
        return SimpleNamespace(
            ship_id=reported.get("id"), ship_type=reported.get("type"), ship_name=reported.get("name"),
            cargo_capacity=reported.get("cargo_capacity"), laden_jump_range_ly=reported.get("laden_jump_range_ly"),
        )

    async def recent_markets(request: Request) -> JSONResponse:
        """The Markets page list: on a hub every node's markets, which peers push up (never relayed)."""
        auth_failure = require_http_auth(request)
        if auth_failure is not None:
            return auth_failure
        snapshots = await asyncio.to_thread(read_recent_markets)
        ship = viewed_ship(request.query_params)
        return JSONResponse(
            {
                "cargo_capacity": _cargo_capacity(ship),
                # The ship's laden range from its Loadout: Best deal's blank-field range.
                "laden_jump_range_ly": getattr(ship, "laden_jump_range_ly", None),
                "markets": [_market_snapshot_payload(snapshot) for snapshot in snapshots],
            }
        )

    async def market_compare(request: Request) -> JSONResponse:
        """Best deal between two listed markets, for the Markets page's ship (`viewed_ship`)."""
        auth_failure = require_http_auth(request)
        if auth_failure is not None:
            return auth_failure
        params = request.query_params
        ship = viewed_ship(params)
        try:
            market_x_id = int(params.get("x", ""))
            market_y_id = int(params.get("y", ""))
            capacity_raw = (params.get("capacity") or "").strip()
            cargo_capacity = int(capacity_raw) if capacity_raw else _cargo_capacity(ship)
        except ValueError:
            return JSONResponse({"detail": "x and y must be market ids; capacity must be a whole number"}, status_code=400)
        if cargo_capacity < 0:
            return JSONResponse({"detail": "capacity must not be negative"}, status_code=400)
        try:
            search_defaults = await asyncio.to_thread(load_haul_search_config)
        except (OSError, HaulSearchConfigError):
            search_defaults = {}
        ship_laden = getattr(ship, "laden_jump_range_ly", None)
        try:
            laden = laden_jump_range(params, search_defaults=search_defaults, ship_laden_ly=ship_laden)
            # The current ship's range, even when the page overrides it, so measured runs compare against it.
            current_laden = laden_jump_range({}, search_defaults=search_defaults, ship_laden_ly=ship_laden)
        except ValueError:
            return JSONResponse({"detail": "laden_jump_range_ly must be a positive number"}, status_code=400)
        window = params.get("window") or MEASURED_WINDOW_DEFAULT
        if window not in MEASURED_WINDOWS:
            return JSONResponse({"detail": f"window must be one of {', '.join(MEASURED_WINDOWS)}"}, status_code=400)
        since, until, _ = parse_window(window, datetime.now(SystemLocalTimezone()))

        def compare() -> dict[str, Any] | None:
            snapshots = read_recent_markets()
            by_id = {snapshot.market_id: snapshot for snapshot in snapshots}
            market_x = by_id.get(market_x_id)
            market_y = by_id.get(market_y_id)
            if market_x is None or market_y is None:
                return None
            comparison = compare_markets(market_items(market_x), market_items(market_y), cargo_capacity)
            return {
                **asdict(comparison),
                **read_trip(market_x, market_y, laden, getattr(ship, "ship_id", None)),
                **read_measured(market_x, market_y, ship, current_laden, window, since, until),
            }

        payload = await asyncio.to_thread(compare)
        if payload is None:
            return JSONResponse({"detail": "market is not in the recent markets list"}, status_code=404)
        return JSONResponse(payload)

    def read_trip(
        market_x: MarketSnapshot, market_y: MarketSnapshot, laden: float, ship_id: int | None
    ) -> dict[str, Any]:
        """Estimated trip time (station facts, here or from the hub) and measured haul profit per hour."""
        stations = [{"market_id": m.market_id, "station": m.station, "system": m.system} for m in (market_x, market_y)]
        hint = None
        if peer_link is not None:
            try:
                reply = peer_link.request(REQUEST_STATION_FACTS, {"stations": stations},
                                          timeout_s=peer_link.request_timeout_s)
                facts = [StationFacts(**{**entry, "coords": _coords(entry.get("coords"))})
                         for entry in reply.body["stations"]]
            except (HubUnreachable, KeyError, TypeError) as exc:
                hint = hub_unreachable_detail(peer_link.hub_label, exc)
                facts = [gather_facts(m.market_id, m.station, m.system, []) for m in (market_x, market_y)]
        else:
            facts = station_facts(stations)
            # A peer without a hub address yet (discovery comes later) owns no station facts.
            hint = "Station facts come from the hub." if market_database_file is None else None
        time_model, time_model_payload = read_time_model(ship_id)
        estimate = estimate_trip(facts[0], facts[1], laden_jump_range_ly=laden, time_model=time_model)
        trip: dict[str, Any] = {
            **asdict(estimate),
            "time_model": time_model_payload,
            "stations": {"x": asdict(facts[0]), "y": asdict(facts[1])},
            "hint": hint,
        }
        if peer_link is not None:
            trip["hub"] = peer_link.hub_label
        return {"trip": trip}

    def read_measured(
        market_x: MarketSnapshot, market_y: MarketSnapshot, ship: Any, current_laden: float,
        window: str, since: datetime | None, until: datetime,
    ) -> dict[str, Any]:
        """Measured profit per hour for the current ship: every node's runs on a hub, this server's own
        standalone, and the hub's answer on a peer."""
        ship_id = getattr(ship, "ship_id", None)
        measured = None
        hint = None
        if peer_link is not None:
            body = {"stations": [{"station": m.station, "system": m.system} for m in (market_x, market_y)],
                    "ship_id": ship_id, "window": window}
            try:
                reply = peer_link.request(REQUEST_MEASURED, body, timeout_s=peer_link.request_timeout_s)
                measured = reply.body["measured"] if reply.status == 200 else None
                if reply.status != 200:
                    hint = f"Hub {peer_link.hub_label}: {reply.body.get('detail')}"
            except (HubUnreachable, KeyError, TypeError, AttributeError) as exc:
                hint = hub_unreachable_detail(peer_link.hub_label, exc)
        else:
            try:
                rows, _ = read_history()
                found = measured_route(rows, market_x, market_y, ship_id=ship_id, since=since, until=until)
                measured = asdict(found) if found is not None else None
            except (OSError, ValueError):
                measured = None
        return {
            "measured": measured,
            "measured_hint": hint,
            "measured_window": window,
            "measured_ship": {
                "id": ship_id, "type": getattr(ship, "ship_type", None), "name": getattr(ship, "ship_name", None),
                "laden_jump_range_ly": current_laden,
            },
        }

    def read_time_model(ship_id: int | None, view: FitShip | None = None) -> tuple[TimeModel, dict[str, Any]]:
        """The trip time model for the ship and its `/api/time-model` payload (`view`: another fit to show);
        a peer asks its hub, which keeps the journal events and the settings, and falls back to its own
        configured model."""
        if peer_link is not None:
            try:
                reply = peer_link.request(REQUEST_TIME_MODEL, {"ship_id": ship_id, "view": view},
                                          timeout_s=peer_link.request_timeout_s)
                model = model_from_payload(reply.body.get("active")) if reply.status == 200 else None
                if model is not None:
                    return model, {**reply.body, "hub": peer_link.hub_label}
            except (HubUnreachable, AttributeError):
                pass
        return time_models.active(ship_id).model, time_models.payload(ship_id, view)

    def own_ship_id() -> int | None:
        return _ship_id_value(getattr(getattr(data_provider(), "ship", None), "ship_id", None))

    def answer_time_model(body: Any) -> LinkReply:
        """A peer's trip time model for its ship."""
        if not isinstance(body, dict):
            return LinkReply(400, {"detail": "body must be a JSON object"})
        try:
            view = parse_fit_ship(body["view"]) if body.get("view") is not None else None
        except ValueError as exc:
            return LinkReply(400, {"detail": str(exc)})
        return LinkReply(200, time_models.payload(_ship_id_value(body.get("ship_id")), view))

    async def time_model_endpoint(params: Mapping[str, str]) -> JSONResponse:
        """Both trip time sets for the viewed node's ship, and which is in use; `fit=` shows another fit.
        The hub answers for any node itself, since it keeps every node's journal events."""
        try:
            view = parse_fit_ship(params["fit"]) if params.get("fit") else None
        except ValueError as exc:
            return JSONResponse({"detail": str(exc)}, status_code=400)
        ship_id = _ship_id_value(getattr(viewed_ship(params), "ship_id", None))
        payload = await asyncio.to_thread(lambda: read_time_model(ship_id, view)[1])
        return JSONResponse(payload)

    def station_facts(stations: list[dict[str, Any]]) -> list[StationFacts]:
        """Facts from this server's store, then Ardent for what it lacks; a peer's requests land here too."""
        store = None
        if market_database_file is not None and market_database_file.exists():
            try:
                store = sqlite3.connect(f"file:{market_database_file}?mode=ro", uri=True)
            except sqlite3.Error:
                store = None
        try:
            sources: list[tuple[str, FactLookup]] = []
            if store is not None:
                sources.append(("store", store_lookup(store)))
            if ardent_lookup is not None:
                # Asked only for what the store lacks; a failed lookup just leaves "-".
                sources.append(("ardent", ardent_lookup))
            return [gather_facts(int(s["market_id"]), str(s["station"]), str(s["system"]), sources) for s in stations]
        finally:
            if store is not None:
                store.close()

    def answer_station_facts(body: Any) -> LinkReply:
        entries = body.get("stations") if isinstance(body, dict) else None
        if not isinstance(entries, list) or not all(
            isinstance(entry, dict) and {"market_id", "station", "system"} <= entry.keys() for entry in entries
        ):
            return LinkReply(400, {"detail": "body must be {\"stations\": [{market_id, station, system}, ...]}"})
        return LinkReply(200, {"stations": [asdict(facts) for facts in station_facts(entries)]})

    def answer_carrier_names(body: Any) -> LinkReply:
        """Fleet carrier display names by callsign, from this server's store; a peer's requests land here too."""
        callsigns = body.get("callsigns") if isinstance(body, dict) else None
        if not isinstance(callsigns, list) or not all(isinstance(callsign, str) for callsign in callsigns):
            return LinkReply(400, {"detail": "body must be {\"callsigns\": [callsign, ...]}"})
        if market_database_file is None or not market_database_file.exists() or not callsigns:
            return LinkReply(200, {"names": {}})
        try:
            store = sqlite3.connect(f"file:{market_database_file}?mode=ro", uri=True)
        except sqlite3.Error as exc:
            return LinkReply(503, {"detail": f"Cannot read the market database: {exc}"})
        try:
            marks = ",".join("?" * len(callsigns))
            rows = store.execute(f"SELECT callsign, name FROM carrier_name WHERE callsign IN ({marks})", callsigns)
            return LinkReply(200, {"names": dict(rows.fetchall())})
        except sqlite3.Error as exc:
            return LinkReply(503, {"detail": f"Cannot read the market database: {exc}"})
        finally:
            store.close()

    async def carrier_names_endpoint(request: Request) -> JSONResponse:
        """`?callsign=Q8N-BVT&callsign=...` -> {"names": {callsign: name}}; only callsigns with a known name."""
        auth_failure = require_http_auth(request)
        if auth_failure is not None:
            return auth_failure
        body = {"callsigns": request.query_params.getlist("callsign")[:200]}
        if peer_link is not None:
            return await ask_hub(REQUEST_CARRIER_NAMES, body)
        return link_reply_response(await asyncio.to_thread(answer_carrier_names, body))

    def answer_measured(body: Any) -> LinkReply:
        """A peer's Best deal measured profit per hour, from the central history."""
        stations = body.get("stations") if isinstance(body, dict) else None
        if not isinstance(stations, list) or len(stations) != 2 or not all(
            isinstance(entry, dict) and isinstance(entry.get("station"), str) and isinstance(entry.get("system"), str)
            for entry in stations
        ):
            return LinkReply(400, {"detail": "body must be {\"stations\": [{station, system}, {station, system}], ...}"})
        ship_id = body.get("ship_id")
        window = body.get("window")
        if (ship_id is not None and (not isinstance(ship_id, int) or isinstance(ship_id, bool))) \
                or window not in MEASURED_WINDOWS:
            return LinkReply(400, {"detail": f"ship_id must be a number or null, window one of {', '.join(MEASURED_WINDOWS)}"})
        since, until, _ = parse_window(window, datetime.now(SystemLocalTimezone()))
        x, y = (StationName(entry["station"], entry["system"]) for entry in stations)
        try:
            rows, _ = read_history()
        except (OSError, ValueError) as exc:
            return LinkReply(503, {"detail": f"Cannot read haul history: {exc}"})
        found = measured_route(rows, x, y, ship_id=ship_id, since=since, until=until)
        return LinkReply(200, {"measured": asdict(found) if found is not None else None})

    def answer_eddn_status(_body: Any) -> LinkReply:
        if eddn_status is None:
            return LinkReply(200, {"enabled": False})
        return LinkReply(200, {"enabled": True, **eddn_status()})

    async def eddn_status_endpoint(request: Request) -> JSONResponse:
        auth_failure = require_http_auth(request)
        if auth_failure is not None:
            return auth_failure
        if peer_link is not None:
            return await ask_hub(REQUEST_EDDN_STATUS, {})
        return link_reply_response(await asyncio.to_thread(answer_eddn_status, {}))

    async def hub_status_endpoint(request: Request) -> JSONResponse:
        auth_failure = require_http_auth(request)
        if auth_failure is not None:
            return auth_failure
        # `muted`: the hub voices this node's callouts, so its own pages say why they are quiet.
        if peer_link is not None:
            return JSONResponse({**await asyncio.to_thread(peer_link.status), "muted": broker.callouts_muted})
        if hub_side is not None:
            local = hub_side.registry.local
            return JSONResponse({"configured": True, "role": "hub", "node_id": local.node_id,
                                 "node_name": local.name, "peers_connected": hub_side.registry.connected_peers(),
                                 "muted": broker.callouts_muted})
        return JSONResponse({"configured": False, "role": "standalone"})

    async def nodes_endpoint(request: Request) -> JSONResponse:
        auth_failure = require_http_auth(request)
        if auth_failure is not None:
            return auth_failure
        if hub_side is None:
            return JSONResponse({"detail": "Only a hub lists nodes"}, status_code=404)
        nodes = hub_side.registry.nodes()
        local_state = await asyncio.to_thread(lambda: node_state(data_provider()))
        return JSONResponse({"nodes": [{**node, "state": local_state} if node["local"] else node for node in nodes]})

    async def hub_voice_endpoint(request: Request) -> JSONResponse:
        """Which node the hub voices and whether its speakers are on (plan 0015 step 7); POST changes them."""
        auth_failure = require_http_auth(request)
        if auth_failure is not None:
            return auth_failure
        if hub_side is None:
            return JSONResponse({"detail": "Only a hub voices nodes"}, status_code=404)
        if request.method == "GET":
            return JSONResponse(hub_side.voice.settings())
        try:
            return JSONResponse(hub_side.voice.update(await request.json()))
        except ValueError as exc:
            return JSONResponse({"detail": str(exc) or "body must be JSON"}, status_code=400)

    async def hub_voice_listen(websocket: WebSocket) -> None:
        """A hub page listening: the voice settings, then every voiced callout (text, WAV or null)."""
        if not auth.is_websocket_authorized(websocket):
            await websocket.close(code=4401, reason="authentication required")
            return
        if hub_side is None:
            await websocket.close(code=4404, reason="not a hub")
            return
        await websocket.accept()
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        remove = hub_side.voice.add_listener(lambda message: loop.call_soon_threadsafe(queue.put_nowait, message))

        async def send() -> None:
            while True:
                await websocket.send_json(await queue.get())

        async def receive() -> None:
            # Only to notice the page going away.
            while True:
                await websocket.receive_text()

        tasks = {asyncio.create_task(send()), asyncio.create_task(receive())}
        try:
            done, pending_tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in pending_tasks:
                task.cancel()
            for task in done:
                task.result()
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            for task in tasks:
                task.cancel()
            remove()

    def route_ship_inputs() -> dict[str, Any]:
        data = data_provider()
        try:
            search_defaults = load_haul_search_config()
        except (OSError, HaulSearchConfigError):
            search_defaults = {}
        return {
            "search_defaults": search_defaults,
            "current_system": getattr(getattr(data, "ship", None), "system", None) or "",
            "cargo_capacity": _ship_cargo_capacity(data),
        }

    def answer_peer_eddn_routes(body: Any) -> LinkReply:
        """A peer's route search, its params resolved for its ship, and its ShipID for the trip time."""
        if not isinstance(body, dict):
            return LinkReply(400, {"detail": "route params must be an object"})
        params = dict(body)
        return answer_eddn_routes(params, _ship_id_value(params.pop("ship_id", None)))

    def answer_eddn_routes(params: Any, ship_id: int | None) -> LinkReply:
        """Routes from this server's market store."""
        if not isinstance(params, dict):
            return LinkReply(400, {"detail": "route params must be an object"})
        if market_database_file is None:
            return LinkReply(404, {"detail": "This peer has no market database; the hub serves routes"})
        if not market_database_file.exists():
            return LinkReply(404, {"detail": "The market database has no data yet"})
        try:
            query = parse_route_query({str(k): str(v) for k, v in params.items()}, **route_ship_inputs())
        except ValueError as exc:
            return LinkReply(400, {"detail": str(exc)})
        names = {item.commodity: item.name for snapshot in read_recent_markets() for item in market_items(snapshot)}
        active = time_models.active(ship_id)
        try:
            payload = run_route_query(
                market_database_file, query, time_model=active.model, display_names=names, now=time.time()
            )
        except RouteQueryError as exc:
            return LinkReply(404, {"detail": str(exc)})
        except sqlite3.Error as exc:
            return LinkReply(503, {"detail": f"Cannot read the market database: {exc}"})
        return LinkReply(200, {**payload, "time_model": time_models.payload(ship_id)})

    async def eddn_routes(query: Mapping[str, str]) -> JSONResponse:
        params = dict(query)
        if peer_link is not None:
            # The hub answers for this ship and this server's search settings, not its own.
            ship_inputs = await asyncio.to_thread(route_ship_inputs)
            body = {**resolve_route_params(params, **ship_inputs), "ship_id": own_ship_id()}
            return await ask_hub(REQUEST_EDDN_ROUTES, body)
        return link_reply_response(await asyncio.to_thread(answer_eddn_routes, params, own_ship_id()))

    def link_reply_response(reply: LinkReply) -> JSONResponse:
        return JSONResponse(reply.body, status_code=reply.status)

    async def ask_hub(kind: str, body: Any) -> JSONResponse:
        assert peer_link is not None
        try:
            reply = await asyncio.to_thread(peer_link.request, kind, body, timeout_s=peer_link.request_timeout_s)
        except HubUnreachable as exc:
            label = peer_link.hub_label
            return JSONResponse({"detail": hub_unreachable_detail(label, exc), "hub": label}, status_code=502)
        return JSONResponse(with_hub_source(reply.body, peer_link.hub_label), status_code=reply.status)

    def answer_haul_search(body: Any) -> LinkReply:
        """A peer's Inara search; it runs here and leaves this server's `haul_search.toml` alone."""
        if not isinstance(body, dict):
            return LinkReply(400, {"detail": "body must be a JSON object", "error_code": "invalid_search"})
        try:
            search = _haul_search_from_payload(body, data=data_provider())
            result = _run_haul_search(search, peer_link=None)
        except _HaulSearchError as exc:
            status_code = 400 if exc.error_code == "invalid_search" else 502
            return LinkReply(status_code, {"detail": exc.message, "error_code": exc.error_code})
        return LinkReply(200, {"result": result})

    link_handlers: dict[str, RequestHandler] = {
        REQUEST_HAUL_SEARCH: answer_haul_search,
        REQUEST_EDDN_ROUTES: answer_peer_eddn_routes,
        REQUEST_TIME_MODEL: answer_time_model,
        REQUEST_EDDN_STATUS: answer_eddn_status,
        REQUEST_STATION_FACTS: answer_station_facts,
        REQUEST_HAUL_STATS: answer_haul_stats,
        REQUEST_MEASURED: answer_measured,
        REQUEST_CARRIER_NAMES: answer_carrier_names,
    }

    async def peer_link_endpoint(websocket: WebSocket) -> None:
        """A peer's link (plan 0015): hub only, hub token required."""
        if hub_side is None:
            await websocket.close(code=4404, reason="not a hub")
            return
        if not SharedAccessTokenAuth(hub_side.token).is_websocket_authorized(websocket):
            await websocket.close(code=4401, reason="hub token required")
            return
        await websocket.accept()
        loop = asyncio.get_running_loop()
        send_lock = asyncio.Lock()
        requests: set[asyncio.Task[None]] = set()

        async def send(frames: list[dict[str, Any]]) -> None:
            async with send_lock:
                for frame in frames:
                    await websocket.send_json(frame)

        def send_soon(frame: dict[str, Any]) -> None:
            """Queue a relay frame (channel or read) from any thread; a closed socket just drops it."""
            future = asyncio.run_coroutine_threadsafe(send([frame]), loop)
            future.add_done_callback(lambda done: done.cancelled() or done.exception())

        session = HubLinkSession(registry=hub_side.registry, store_item=hub_side.store_item, handlers=link_handlers,
                                 relay=hub_side.relay, callout=hub_side.voice.callout,
                                 linked=hub_side.voice.node_linked, send=send_soon,
                                 log=logging.getLogger("edcr.hub").info)

        async def answer(frame: dict[str, Any]) -> None:
            await send(await asyncio.to_thread(session.receive, frame))

        try:
            while not session.closed:
                frame = await websocket.receive_json()
                if session.hello is not None and isinstance(frame, dict) and frame.get("type") == "request":
                    # Searches take minutes; answer them alongside acks and pings.
                    task = asyncio.create_task(answer(frame))
                    requests.add(task)
                    task.add_done_callback(requests.discard)
                    continue
                await send(await asyncio.to_thread(session.receive, frame))
            await websocket.close(code=4400)
        except (WebSocketDisconnect, ValueError, RuntimeError):
            pass
        finally:
            for task in requests:
                task.cancel()
            session.close()

    async def spansh_route(params: Mapping[str, str]) -> JSONResponse:
        source_system = (params.get("from") or "").strip()
        destination_system = (params.get("to") or "").strip()
        range_raw = params.get("range")
        if not source_system or not destination_system or not range_raw:
            return JSONResponse(
                {"detail": "from, to, and range are required"},
                status_code=400,
            )
        try:
            range_ly = float(range_raw)
            efficiency = int(params.get("efficiency", "60"))
            supercharge_multiplier = int(params.get("supercharge_multiplier", "4"))
        except ValueError as exc:
            return JSONResponse({"detail": f"invalid numeric parameter: {exc}"}, status_code=400)
        try:
            _, route_id, payload = await asyncio.to_thread(
                fetch_and_cache_spansh_route,
                broker=broker,
                source_system=source_system,
                destination_system=destination_system,
                range_ly=range_ly,
                efficiency=efficiency,
                supercharge_multiplier=supercharge_multiplier,
            )
        except RouteCompareError as exc:
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
        return JSONResponse(payload)

    async def run_command(body: Any) -> JSONResponse:
        raw_input = body.get("raw_input") if isinstance(body, dict) else None
        if not isinstance(raw_input, str) or not raw_input.strip():
            return JSONResponse({"detail": "raw_input must be a non-empty command string"}, status_code=400)
        skip_delay = body.get("skip_delay")
        if skip_delay is not None and not isinstance(skip_delay, bool):
            return JSONResponse({"detail": "skip_delay must be true or false"}, status_code=400)
        if command_handler is None:
            return JSONResponse({"detail": "command execution is not available on this server"}, status_code=503)
        raw_input = raw_input.strip()
        try:
            # Same synchronous call as the websocket command.submit_input path.
            accepted = command_handler.submit_input(raw_input, skip_delay=skip_delay)
        except Exception as exc:
            logger.exception("submit_input dispatch failed")
            return JSONResponse({"detail": str(exc) or "command execution failed"}, status_code=500)
        routine = data_provider().routine
        payload = {
            "accepted": accepted,
            "raw_input": raw_input,
            "routine_active": routine.routine_active,
            "active_routine_name": routine.active_routine_name,
        }
        if not accepted:
            busy_name = routine.active_routine_name or "a routine"
            payload["detail"] = f"Refused: {busy_name} is already running. Stop it or wait for it to finish."
            return JSONResponse(payload, status_code=409)
        return JSONResponse(payload)

    async def stop_routine(body: Any) -> JSONResponse:
        mode = body.get("mode", "now") if isinstance(body, dict) else None
        if mode not in {"now", "after_run"}:
            return JSONResponse({"detail": "mode must be now or after_run"}, status_code=400)
        if command_handler is None:
            return JSONResponse({"detail": "command execution is not available on this server"}, status_code=503)
        data = data_provider()
        routine = data.routine
        tracking = data.haul_session.tracking and data.haul_session.active
        if not routine.routine_active and not tracking:
            return JSONResponse(
                {"accepted": False, "routine_active": False, "active_routine_name": None,
                 "detail": "No routine is running."},
                status_code=409,
            )
        command_handler.cancel_active_routine(stop_mode=mode)
        after = data_provider().routine
        return JSONResponse(
            {
                "accepted": True,
                "mode": mode,
                "stopped_routine_name": routine.active_routine_name if routine.routine_active else "haul tracking",
                "routine_active": after.routine_active,
                "active_routine_name": after.active_routine_name,
            }
        )

    async def session(websocket: WebSocket) -> None:
        if not auth.is_websocket_authorized(websocket):
            await websocket.close(code=4401, reason="authentication required")
            return
        client_name = websocket.query_params.get("client_name", "observer-client")
        node_id = viewed_node(websocket.query_params)
        if node_id is not None:
            await relayed_session(websocket, node_id, client_name)
            return
        await websocket.accept()
        observer = broker.register_observer(client_name)
        try:
            for message in session_start_messages(observer.session_id, data_provider, broker,
                                                  client_role=broker.current_session_role(observer.session_id)):
                await websocket.send_json(message)
            sender = asyncio.create_task(_send_session_messages(websocket, observer))
            receiver = asyncio.create_task(
                _receive_session_messages(
                    websocket,
                    observer=observer,
                    command_handler=command_handler,
                    broker=broker,
                    data_provider=data_provider,
                    journal_dir=journal_dir,
                    peer_link=peer_link,
                    route_compare_navroute_wait_seconds=route_compare_navroute_wait_seconds,
                    route_compare_compare_retry_attempts=route_compare_compare_retry_attempts,
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

    # Plan 0015 step 5: a hub page looks at one node with `?node=<node_id>`; the hub's own game needs none.
    relay = hub_side.relay if hub_side is not None else None

    def viewed_node(params: Mapping[str, str]) -> str | None:
        """The peer a hub page looks at, or None for this server's own game (always on a peer or standalone)."""
        node_id = (params.get("node") or "").strip()
        if hub_side is None or not node_id or node_id == hub_side.registry.local.node_id:
            return None
        return node_id

    # Page reads that answer for the node a page looks at; a hub relays them to a peer, and the peer
    # answers them here too. Hub-owned data (history, EDDN status, hub status) is not among them.
    node_reads: dict[str, Callable[[Mapping[str, str]], Awaitable[JSONResponse]]] = {
        "/api/route-compare": route_compare,
        "/api/route-compare/config": route_compare_config,
        "/api/spansh-route": spansh_route,
        "/api/eddn-routes": eddn_routes,
        "/api/journal-ledger": journal_ledger,
    }
    assert node_reads.keys() == NODE_READS
    # Page actions that run on the node a page drives (plan 0015 step 6); the body is JSON.
    node_actions: dict[str, Callable[[Any], Awaitable[JSONResponse]]] = {
        "/api/command": run_command,
        "/api/stop": stop_routine,
    }
    assert node_actions.keys() == NODE_ACTIONS

    def node_action_endpoint(path: str, *, empty_body: object | None) -> Callable[[Request], Awaitable[JSONResponse]]:
        """POST `path` here, or on the node a hub page drives. `empty_body` stands in for no body (None: required)."""
        act = node_actions[path]

        async def endpoint(request: Request) -> JSONResponse:
            auth_failure = require_http_auth(request)
            if auth_failure is not None:
                return auth_failure
            body = empty_body
            if body is None or await request.body():
                try:
                    body = await request.json()
                except ValueError:
                    return JSONResponse({"detail": "body must be JSON"}, status_code=400)
            node_id = viewed_node(request.query_params)
            if node_id is None:
                return await act(body)
            assert relay is not None
            try:
                reply = await asyncio.to_thread(relay.act, node_id, path, body)
            except NodeOffline as exc:
                return JSONResponse({"detail": f"Node {relay.name(node_id)} is unreachable: {exc}", "node": node_id},
                                    status_code=502)
            return link_reply_response(reply)

        return endpoint

    # Hub pages' work on this peer runs on one loop, as a local page's runs on the server's.
    node_loop = NodeLoop()

    def answer_node_action(path: str, body: Any) -> LinkReply:
        """A hub page's command or stop on this peer, as if posted here (called off the loop)."""
        response = node_loop.run(node_actions[path](body))
        return LinkReply(response.status_code, json.loads(bytes(response.body)))

    def answer_node_command(channel_id: str, message: dict[str, Any]) -> dict[str, Any] | None:
        """A hub page's session command on this peer, through the same handler as a local page's."""
        if message.get("message_type") == "command.request_active_operator":
            # Hub pages are not sessions on this server; they all drive it alike.
            return relay_error(message.get("message_id"), "unsupported_message_type",
                               "Hub pages do not claim the operator role on a node.")
        return node_loop.run(_handle_session_message_async(
            message,
            session_id=channel_id,
            client_role="active_operator",
            command_handler=command_handler,
            broker=broker,
            data_provider=data_provider,
            journal_dir=journal_dir,
            peer_link=peer_link,
            route_compare_navroute_wait_seconds=route_compare_navroute_wait_seconds,
            route_compare_compare_retry_attempts=route_compare_compare_retry_attempts,
        ))

    async def time_model_route(request: Request) -> JSONResponse:
        """GET: both trip time sets for the viewed node's ship. POST: save the configured set and which set
        is used, into `config.toml`, live. Only the server that keeps the journal events saves them."""
        auth_failure = require_http_auth(request)
        if auth_failure is not None:
            return auth_failure
        if request.method == "GET":
            response = await time_model_endpoint(request.query_params)
            if response.status_code != 200:
                return response
            # Whether this server's page may save; a peer's answer from its hub says "hub".
            return JSONResponse({**json.loads(bytes(response.body)), "editable": peer_link is None})
        if peer_link is not None:
            return JSONResponse({"detail": f"The trip time settings live on the hub {peer_link.hub_label}; "
                                           "change them on its /config page"}, status_code=409)
        if config_file is None:
            return JSONResponse({"detail": "This server has no config file to save to"}, status_code=503)
        try:
            body = await request.json()
            model, source, fit_ship = _time_model_update(body, time_models.configured, time_models.source,
                                                         time_models.fit_ship)
        except ValueError as exc:
            return JSONResponse({"detail": str(exc) or "body must be JSON"}, status_code=400)
        try:
            await asyncio.to_thread(save_time_model, config_file, model, source, fit_ship)
        except (OSError, ConfigError) as exc:
            return JSONResponse({"detail": f"Cannot save {config_file}: {exc}"}, status_code=500)
        time_models.set_configured(model, source, fit_ship)
        return JSONResponse({**await asyncio.to_thread(time_models.payload, own_ship_id()), "editable": True})

    def node_read_endpoint(path: str) -> Callable[[Request], Awaitable[JSONResponse]]:
        read = node_reads[path]

        async def endpoint(request: Request) -> JSONResponse:
            auth_failure = require_http_auth(request)
            if auth_failure is not None:
                return auth_failure
            node_id = viewed_node(request.query_params)
            if node_id is None:
                return await read(request.query_params)
            assert relay is not None
            params = {key: value for key, value in request.query_params.items()
                      if key not in {"node", ACCESS_TOKEN_QUERY_PARAMETER}}
            try:
                reply = await asyncio.to_thread(relay.read, node_id, path, params)
            except NodeOffline as exc:
                name = relay.name(node_id)
                return JSONResponse({"detail": f"Node {name} is unreachable: {exc}", "node": node_id}, status_code=502)
            return link_reply_response(reply)

        return endpoint

    def answer_node_read(path: str, params: dict[str, str]) -> LinkReply:
        """A hub page's read on this peer, called off the loop (it may ask the hub in turn)."""
        response = node_loop.run(node_reads[path](params))
        return LinkReply(response.status_code, json.loads(bytes(response.body)))

    def open_node_session(session_id: str) -> list[dict[str, Any]]:
        """The first messages of a hub page's channel on this peer, as a local page gets them."""
        # Hub pages drive the node (plan 0015), so they get the operator controls a local operator page gets.
        return session_start_messages(session_id, data_provider, broker, client_role="active_operator")

    async def relayed_session(websocket: WebSocket, node_id: str, client_name: str) -> None:
        """Stream a peer's session to a hub page and send the page's commands to it. While the peer is
        away the page stays connected, is told so once, and gets a fresh hydrate when the peer links
        again. A command the peer does not answer in time, or that is cut off by the link closing,
        gets a `node_unreachable` error, so the page never waits on it."""
        assert relay is not None
        await websocket.accept()
        loop = asyncio.get_running_loop()
        # Session messages, or the reason the channel ended (a str).
        queue: asyncio.Queue[dict[str, Any] | str] = asyncio.Queue()
        send_lock = asyncio.Lock()
        # Commands sent to the node and not answered yet: message id -> their timeout.
        pending: dict[str, asyncio.TimerHandle] = {}

        async def send(message: dict[str, Any]) -> None:
            async with send_lock:
                await websocket.send_json(message)

        def deliver(message: dict[str, Any]) -> None:
            loop.call_soon_threadsafe(queue.put_nowait, message)

        def end(detail: str) -> None:
            loop.call_soon_threadsafe(queue.put_nowait, detail)

        def unreachable(message_id: str, detail: str) -> dict[str, Any]:
            return relay_error(message_id, "node_unreachable", f"Node {relay.name(node_id)} is unreachable: {detail}")

        def expire(message_id: str, timeout_s: float) -> None:
            if pending.pop(message_id, None) is not None:
                queue.put_nowait(unreachable(message_id, f"no answer in {timeout_s:g} s"))

        channel_id: str | None = None

        async def pump() -> None:
            nonlocal channel_id
            told_offline = False
            while True:
                try:
                    channel_id = relay.open_channel(node_id, client_name, deliver, end)
                except NodeOffline as exc:
                    if not told_offline:
                        await send(node_offline_message(relay.name(node_id), str(exc)))
                        told_offline = True
                    await asyncio.sleep(NODE_RETRY_S)
                    continue
                told_offline = False
                while True:
                    item = await queue.get()
                    if isinstance(item, str):
                        channel_id = None
                        for message_id, timer in list(pending.items()):
                            timer.cancel()
                            await send(unreachable(message_id, item))
                        pending.clear()
                        await send(node_offline_message(relay.name(node_id), item))
                        told_offline = True
                        break
                    answered = item.get("correlation_message_id")
                    timer = pending.pop(answered, None) if isinstance(answered, str) else None
                    if timer is not None:
                        timer.cancel()
                    await send(item)
                await asyncio.sleep(NODE_RETRY_S)

        async def forward_commands() -> None:
            while True:
                message = await websocket.receive_json()
                if not isinstance(message, dict) or not str(message.get("message_type", "")).startswith("command."):
                    continue
                message_id = message.get("message_id")
                message_id = str(message_id) if message_id is not None else None
                if channel_id is None:
                    if message_id is not None:
                        await send(unreachable(message_id, "not linked to the hub"))
                    continue
                if message_id is not None:
                    timeout_s = relay.command_timeout_s(str(message["message_type"]))
                    pending[message_id] = loop.call_later(timeout_s, expire, message_id, timeout_s)
                try:
                    await asyncio.to_thread(relay.command, channel_id, message)
                except NodeOffline as exc:
                    timer = pending.pop(message_id, None) if message_id is not None else None
                    if timer is not None:
                        timer.cancel()
                        await send(unreachable(message_id, str(exc)))

        tasks = {asyncio.create_task(pump()), asyncio.create_task(forward_commands())}
        try:
            done, pending_tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in pending_tasks:
                task.cancel()
            for task in done:
                task.result()
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            for task in tasks:
                task.cancel()
            for timer in pending.values():
                timer.cancel()
            if channel_id is not None:
                relay.close_channel(channel_id)

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
            Route(CONTROLS_WEB_URL_PATH, controls_web),
            Route(MARKETS_WEB_URL_PATH, markets_web),
            Route(ROUTES_WEB_URL_PATH, routes_web),
            Route(TRAVEL_WEB_URL_PATH, travel_web),
            Route(CONFIG_WEB_URL_PATH, config_web),
            Route("/api/route-compare", node_read_endpoint("/api/route-compare")),
            Route("/api/route-compare/config", node_read_endpoint("/api/route-compare/config")),
            Route("/api/spansh-route", node_read_endpoint("/api/spansh-route")),
            Route("/api/haul-stats", haul_stats_endpoint),
            Route("/api/recent-markets", recent_markets),
            Route("/api/market-compare", market_compare),
            Route("/api/eddn-status", eddn_status_endpoint),
            Route("/api/carrier-names", carrier_names_endpoint),
            Route("/api/eddn-routes", node_read_endpoint("/api/eddn-routes")),
            Route("/api/time-model", time_model_route, methods=["GET", "POST"]),
            Route("/api/hub-status", hub_status_endpoint),
            Route("/api/nodes", nodes_endpoint),
            Route("/api/hub-voice", hub_voice_endpoint, methods=["GET", "POST"]),
            Route("/api/command", node_action_endpoint("/api/command", empty_body=None), methods=["POST"]),
            Route("/api/stop", node_action_endpoint("/api/stop", empty_body={}), methods=["POST"]),
            Route(HAUL_WEB_ASSET_URL_PATH, haul_web_asset),
            Route("/favicon.ico", favicon),
            WebSocketRoute("/session", session),
            WebSocketRoute(PEER_LINK_PATH, peer_link_endpoint),
            WebSocketRoute("/api/hub-voice/listen", hub_voice_listen),
        ]
    )
    # The hub's answers to peer requests, so tests drive a link session without a socket.
    app.state.link_handlers = link_handlers
    # A peer answers hub pages' channels and reads with these (`edcr.hub.relay.PeerRelay`).
    app.state.answer_node_read = answer_node_read
    app.state.answer_node_command = answer_node_command
    app.state.answer_node_action = answer_node_action
    app.state.open_node_session = open_node_session
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    async def _log_unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse({"detail": "internal server error"}, status_code=500)

    app.add_exception_handler(Exception, _log_unhandled_exception)
    return app


# Seconds between a hub page's tries to reach a node that is offline.
NODE_RETRY_S = 2.0


def node_offline_message(node_name: str, detail: str) -> dict[str, Any]:
    """Tells a hub page the node it looks at went away, as an activity log line."""
    stamp = datetime.now(SystemLocalTimezone()).isoformat(timespec="seconds")
    return protocol_message("event.activity_log_appended", {"entry": {
        "entry_id": f"node-offline-{time.time_ns()}", "timestamp": stamp,
        "message_text": f"Node {node_name} is offline ({detail}); showing it again when it links.",
        "severity": "error",
    }})


def session_start_messages(
    session_id: str, data_provider: Callable[[], object], broker: InMemoryObserverSessionBroker, *, client_role: str,
) -> list[dict[str, Any]]:
    """What a session gets first: connection ready, then the hydrate."""
    data = data_provider()
    return [
        protocol_message(
            "event.connection_ready",
            {
                "session_id": session_id,
                "server_name": data.server_status.server_name,
                "server_version": data.server_status.server_version,
                "client_role": client_role,
                "capability_names": data.server_status.capability_names,
            },
        ),
        hydrate_message(_server_hydrate_data(data_provider(), broker=broker)),
    ]


# Best deal's measured profit per hour window choices (haul_history.parse_window labels).
MEASURED_WINDOWS = ("48h", "7d", "30d", "all")
MEASURED_WINDOW_DEFAULT = "7d"


def _time_model_update(
    body: Any, configured: TimeModel, source: str, fit_ship: FitShip
) -> tuple[TimeModel, str, FitShip]:
    """The configured trip time set, source and fit after a `POST /api/time-model` body; fields left out stay."""
    if not isinstance(body, dict):
        raise ValueError("body must be a JSON object")
    source = body.get("source", source)
    if source not in TIME_MODEL_SOURCES:
        raise ValueError(f"source must be one of {', '.join(TIME_MODEL_SOURCES)}")
    values = body.get("configured", {})
    if not isinstance(values, dict):
        raise ValueError("configured must be an object of trip time fields")
    unknown = sorted(set(values) - set(TimeModel.__dataclass_fields__))
    if unknown:
        raise ValueError(f"Unknown trip time fields: {', '.join(unknown)}")
    for name, value in values.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError(f"{name} must be zero or a positive number")
    fit_ship = parse_fit_ship(body.get("fit_ship", fit_ship))
    return replace(configured, **{name: float(value) for name, value in values.items()}), source, fit_ship


def _ship_id_value(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _ship_cargo_capacity(data: object) -> int:
    return _cargo_capacity(getattr(data, "ship", None))


def _cargo_capacity(ship: object) -> int:
    cargo_capacity = getattr(ship, "cargo_capacity", None)
    return cargo_capacity if isinstance(cargo_capacity, int) and cargo_capacity > 0 else 0


def _market_snapshot_payload(snapshot: MarketSnapshot) -> dict[str, Any]:
    return {
        "market_id": snapshot.market_id,
        "station": snapshot.station,
        "system": snapshot.system,
        "station_type": snapshot.station_type,
        "timestamp": snapshot.timestamp,
        "items": [asdict(item) for item in market_items(snapshot)],
    }


class RouteCompareError(Exception):
    def __init__(self, *, status_code: int, detail: str, retryable: bool) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
        self.retryable = retryable


def _spansh_route_error(exc: httpx.HTTPStatusError) -> RouteCompareError:
    """Turn a Spansh HTTP error into an actionable web/API error."""
    response = exc.response
    upstream_error: str | None = None
    try:
        payload = response.json()
        if isinstance(payload, dict) and isinstance(payload.get("error"), str):
            upstream_error = payload["error"]
    except (ValueError, TypeError):
        pass

    if upstream_error == "Could not find finishing system":
        detail = "Spansh says could not find target system"
    elif upstream_error:
        detail = f"Spansh says: {upstream_error}"
    else:
        detail = f"Spansh route request failed: {exc}"
    status_code = response.status_code if response.status_code < 500 else 502
    return RouteCompareError(status_code=status_code, detail=detail, retryable=False)


def fetch_and_cache_spansh_route(
    *,
    broker: InMemoryObserverSessionBroker,
    source_system: str,
    destination_system: str,
    range_ly: float,
    efficiency: int,
    supercharge_multiplier: int,
) -> tuple[Any, str, dict[str, Any]]:
    try:
        spansh = plot_route(
            source_system=source_system,
            destination_system=destination_system,
            range_ly=range_ly,
            efficiency=efficiency,
            supercharge_multiplier=supercharge_multiplier,
        )
    except httpx.HTTPStatusError as exc:
        logger.exception("spansh route fetch failed; response=%s", exc.response.text)
        raise _spansh_route_error(exc) from exc
    except Exception as exc:
        logger.exception("spansh route fetch failed")
        raise RouteCompareError(
            status_code=502,
            detail=f"spansh route fetch failed: {exc}",
            retryable=True,
        ) from exc
    request_key = RouteRequestKey(
        source_system=spansh.source_system,
        destination_system=spansh.destination_system,
        range_ly=range_ly,
        efficiency=efficiency,
        supercharge_multiplier=supercharge_multiplier,
    )
    route_id = broker.server_state.cache_spansh_route(spansh, request_key=request_key)
    payload = {"spansh": route_payload(spansh), "route_id": route_id}
    return spansh, route_id, payload


def build_and_cache_live_comparison(
    *,
    broker: InMemoryObserverSessionBroker,
    journal_dir: Path | None,
    source_system: str,
    destination_system: str,
    range_ly: float,
    efficiency: int,
    supercharge_multiplier: int,
) -> dict[str, Any]:
    if journal_dir is None:
        raise RouteCompareError(
            status_code=503,
            detail="server has no journal_dir configured; live comparison unavailable",
            retryable=False,
        )
    try:
        comparison = build_live_comparison(
            journal_dir=journal_dir,
            source_system=source_system,
            destination_system=destination_system,
            range_ly=range_ly,
            efficiency=efficiency,
            supercharge_multiplier=supercharge_multiplier,
        )
    except FileNotFoundError as exc:
        raise RouteCompareError(
            status_code=404,
            detail="NavRoute.json not found; plot a route in game first",
            retryable=True,
        ) from exc
    except httpx.HTTPStatusError as exc:
        logger.exception("Spansh route comparison failed; response=%s", exc.response.text)
        raise _spansh_route_error(exc) from exc
    except Exception as exc:
        logger.exception("route comparison failed")
        raise RouteCompareError(
            status_code=502,
            detail=f"route comparison failed: {exc}",
            retryable=False,
        ) from exc
    _publish_spansh_route_ready(broker, comparison)
    route_id = _cache_comparison_spansh_route(broker, comparison, range_ly=range_ly)
    payload = comparison_to_payload(comparison)
    payload["route_id"] = route_id
    return payload


def _cache_comparison_spansh_route(
    broker: InMemoryObserverSessionBroker,
    comparison: RouteComparison,
    *,
    range_ly: float,
) -> str:
    metadata = comparison.spansh.metadata
    efficiency = metadata.efficiency if isinstance(metadata, SpanshMetadata) else 60
    supercharge_multiplier = metadata.supercharge_multiplier if isinstance(metadata, SpanshMetadata) else 4
    request_key = RouteRequestKey(
        source_system=comparison.spansh.source_system,
        destination_system=comparison.spansh.destination_system,
        range_ly=range_ly,
        efficiency=efficiency,
        supercharge_multiplier=supercharge_multiplier,
    )
    return broker.server_state.cache_spansh_route(comparison.spansh, request_key=request_key)


def _publish_spansh_route_ready(
    broker: InMemoryObserverSessionBroker,
    comparison: RouteComparison,
) -> None:
    message_values: dict[str, Any] = {
        "jump_summary": comparison.jump_summary,
        "neutron_summary": comparison.neutron_summary,
    }
    broker.publish_announcement(
        build_announcement_event(
            announcement_id=AnnouncementId.SPANSH_ROUTE_READY.value,
            message_text=comparison.tts_phrase,
            message_values=message_values,
        )
    )


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
    active_spansh_route = _active_spansh_route_payload(broker)
    return replace(
        data,
        selected_trade_route=selected_trade_route,
        running_trade_route=running_trade_route,
        active_spansh_route=active_spansh_route,
    )


def _active_spansh_route_payload(broker: InMemoryObserverSessionBroker) -> dict[str, Any] | None:
    route_id = broker.server_state.active_spansh_route_id()
    if not route_id:
        return None
    route = broker.server_state.get_spansh_route(route_id)
    if route is None:
        return None
    return {"route_id": route_id, "route": route_payload(route)}


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
    peer_link: PeerLink | None,
) -> dict[str, object]:
    message_id_value = message.get("message_id")
    correlation_message_id = message_id_value if isinstance(message_id_value, str) else None
    payload_value = message.get("payload", {})
    payload = payload_value if isinstance(payload_value, dict) else {}
    if data_provider is None:
        return _transport_unavailable_error(correlation_message_id)
    try:
        search = _haul_search_from_payload(payload, data=data_provider())
        await asyncio.to_thread(_save_haul_search_defaults, search.query_params)
        result = await asyncio.to_thread(_run_haul_search, search, peer_link=peer_link)
    except _HaulSearchError as exc:
        return _haul_search_error_response(exc, correlation_message_id)
    return _haul_search_success_response(result, correlation_message_id)


async def _handle_dispatch_route_all_in_one_async(
    message: dict[str, object],
    *,
    command_handler: ObserverSessionCommandHandler | None,
    broker: InMemoryObserverSessionBroker,
    journal_dir: Path | None,
    navroute_wait_seconds_default: float,
    compare_retry_attempts_default: int,
) -> dict[str, object]:
    message_id_value = message.get("message_id")
    correlation_message_id = message_id_value if isinstance(message_id_value, str) else None
    payload_value = message.get("payload", {})
    payload = payload_value if isinstance(payload_value, dict) else {}
    if command_handler is None:
        return _transport_unavailable_error(correlation_message_id)

    source_system = _payload_string(payload, "from")
    destination_system = _payload_string(payload, "to")
    if not source_system or not destination_system:
        return _response_error(
            "invalid_command",
            "Route all-in-one requires from and to system names.",
            retryable=True,
            correlation_message_id=correlation_message_id,
        )
    try:
        range_ly = float(payload["range"])
    except (KeyError, TypeError, ValueError):
        return _response_error(
            "invalid_command",
            "Route all-in-one requires numeric range.",
            retryable=True,
            correlation_message_id=correlation_message_id,
        )
    try:
        efficiency = int(payload.get("efficiency", 60))
        supercharge_multiplier = int(payload.get("supercharge_multiplier", 4))
    except (TypeError, ValueError):
        return _response_error(
            "invalid_command",
            "Route all-in-one efficiency and supercharge_multiplier must be integers.",
            retryable=True,
            correlation_message_id=correlation_message_id,
        )
    galaxy_map_settle_value = payload.get("galaxy_map_settle")
    if not isinstance(galaxy_map_settle_value, (int, float)):
        return _response_error(
            "invalid_command",
            "Route all-in-one requires a numeric galaxy_map_settle.",
            retryable=True,
            correlation_message_id=correlation_message_id,
        )
    galaxy_map_settle = float(galaxy_map_settle_value)
    station = _payload_string(payload, "station")

    navroute_wait_value = payload.get("navroute_wait_seconds")
    navroute_wait_seconds = (
        float(navroute_wait_value)
        if isinstance(navroute_wait_value, (int, float)) and navroute_wait_value >= 0
        else navroute_wait_seconds_default
    )
    compare_retry_value = payload.get("compare_retry_attempts")
    compare_retry_attempts = (
        int(compare_retry_value)
        if isinstance(compare_retry_value, int) and compare_retry_value >= 1
        else compare_retry_attempts_default
    )
    raw_command_value = payload.get("raw_command")
    raw_command = raw_command_value if isinstance(raw_command_value, str) else None
    skip_delay_value = payload.get("skip_delay")
    skip_delay = bool(skip_delay_value) if isinstance(skip_delay_value, bool) else False

    phases: list[dict[str, Any]] = []

    try:
        command_handler.dispatch_destination(
            destination_system,
            galaxy_map_settle,
            skip_delay=skip_delay,
            raw_command=raw_command,
        )
    except Exception as exc:
        logger.exception("route all-in-one: dispatch_destination failed")
        return _command_execution_failed_error(exc, correlation_message_id)
    phases.append({"phase": "dispatch_destination", "status": "ok", "destination_system": destination_system})

    try:
        _spansh, spansh_route_id, spansh_payload = await asyncio.to_thread(
            fetch_and_cache_spansh_route,
            broker=broker,
            source_system=source_system,
            destination_system=destination_system,
            range_ly=range_ly,
            efficiency=efficiency,
            supercharge_multiplier=supercharge_multiplier,
        )
    except RouteCompareError as exc:
        phases.append({"phase": "fetch_spansh", "status": "error", "detail": exc.detail})
        return _response_error(
            "route_all_in_one_spansh_failed",
            exc.detail,
            retryable=exc.retryable,
            correlation_message_id=correlation_message_id,
        )
    phases.append({
        "phase": "fetch_spansh",
        "status": "ok",
        "route_id": spansh_route_id,
        "waypoint_count": len(spansh_payload["spansh"]["waypoints"]),
    })

    last_error: RouteCompareError | None = None
    comparison_payload: dict[str, Any] | None = None
    for attempt in range(1, compare_retry_attempts + 1):
        await asyncio.sleep(navroute_wait_seconds)
        try:
            comparison_payload = await asyncio.to_thread(
                build_and_cache_live_comparison,
                broker=broker,
                journal_dir=journal_dir,
                source_system=source_system,
                destination_system=destination_system,
                range_ly=range_ly,
                efficiency=efficiency,
                supercharge_multiplier=supercharge_multiplier,
            )
        except RouteCompareError as exc:
            last_error = exc
            phases.append({
                "phase": "compare",
                "status": "retryable" if exc.retryable and attempt < compare_retry_attempts else "error",
                "attempt": attempt,
                "detail": exc.detail,
            })
            if not exc.retryable or attempt >= compare_retry_attempts:
                return _response_error(
                    "route_all_in_one_compare_failed",
                    exc.detail,
                    retryable=exc.retryable,
                    correlation_message_id=correlation_message_id,
                )
            continue
        phases.append({"phase": "compare", "status": "ok", "attempt": attempt})
        break

    if comparison_payload is None:
        detail = last_error.detail if last_error else "route comparison did not complete"
        return _response_error(
            "route_all_in_one_compare_failed",
            detail,
            retryable=True,
            correlation_message_id=correlation_message_id,
        )

    return protocol_message(
        "response.success",
        {
            "accepted": True,
            "message_text": "Route all-in-one complete.",
            "result": {
                "route_id": comparison_payload.get("route_id"),
                "comparison": comparison_payload,
                "phases": phases,
                "navroute_wait_seconds": navroute_wait_seconds,
                "compare_retry_attempts": compare_retry_attempts,
            },
        },
        correlation_message_id=correlation_message_id,
    )


@dataclass(frozen=True)
class _HaulSearch:
    system_name: str
    query_params: dict[str, str]
    destination_filter: str


class _HaulSearchError(Exception):
    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


def _haul_search_from_payload(payload: dict[str, Any], *, data: object) -> _HaulSearch:
    """Read an Inara search request; origin and cargo fall back to this server's ship."""
    system_name = _payload_string(payload, "system_name") or _payload_string(payload, "origin")
    if not system_name:
        system_name = (getattr(getattr(data, "ship", None), "system", "") or "").strip()
    if not system_name:
        raise _HaulSearchError("invalid_search", "Haul search needs an origin system.")
    try:
        query_params = _haul_search_query_params(payload, data=data)
    except ValueError as exc:
        raise _HaulSearchError("invalid_search", str(exc)) from exc
    destination_filter = _payload_string(payload, "destination") or _payload_string(payload, "destination_filter")
    return _HaulSearch(system_name, query_params, destination_filter)


def _coords(value: object) -> tuple[float, float, float] | None:
    """Coordinates from JSON, where tuples arrive as lists."""
    if isinstance(value, (list, tuple)) and len(value) == 3:
        return (float(value[0]), float(value[1]), float(value[2]))
    return None


def _run_haul_search(search: _HaulSearch, *, peer_link: PeerLink | None) -> dict[str, Any]:
    """Search Inara here, or ask the hub on a peer; blocks, so run it off the event loop."""
    if peer_link is not None:
        return _run_hub_haul_search(search, peer_link)
    try:
        result = search_trade_routes(search.system_name, query_params=search.query_params)
    except Exception as exc:
        logger.exception("haul search failed")
        raise _HaulSearchError("haul_search_failed", str(exc) or "Failed to search haul routes.") from exc
    routes = list(result.routes)
    unfiltered_count = len(routes)
    if search.destination_filter:
        routes = [route for route in routes if _route_matches_destination(route, search.destination_filter)]
    return _haul_search_response(
        result,
        routes=routes,
        unfiltered_count=unfiltered_count,
        use_surface_stations=search.query_params["use_surface_stations"],
    )


def _run_hub_haul_search(search: _HaulSearch, peer_link: PeerLink) -> dict[str, Any]:
    # The query params use the payload's own keys, so the hub reads them back unchanged.
    body = {**search.query_params, "system_name": search.system_name, "destination": search.destination_filter}
    label = peer_link.hub_label
    try:
        reply = peer_link.request(REQUEST_HAUL_SEARCH, body, timeout_s=peer_link.search_timeout_s)
    except HubUnreachable as exc:
        raise _HaulSearchError("hub_unreachable", hub_unreachable_detail(label, exc)) from exc
    payload = reply.body if isinstance(reply.body, dict) else {}
    result = payload.get("result")
    if reply.status != 200 or not isinstance(result, dict):
        detail = payload.get("detail") or f"status {reply.status}"
        raise _HaulSearchError(str(payload.get("error_code") or "haul_search_failed"), f"Hub {label}: {detail}")
    return with_hub_source(result, label)


def _haul_search_error_response(exc: _HaulSearchError, correlation_message_id: str | None) -> dict[str, object]:
    return _response_error(exc.error_code, exc.message, retryable=True, correlation_message_id=correlation_message_id)


def _haul_search_success_response(result: dict[str, Any], correlation_message_id: str | None) -> dict[str, object]:
    return protocol_message(
        "response.success",
        {"accepted": True, "message_text": "Haul search complete.", "result": result},
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

    surface_stations = parse_surface_stations(_payload_string(payload, "use_surface_stations"), default="no")
    if surface_stations is None:
        raise ValueError("Surface stations must be no, yes_with_odyssey or yes_exclude_odyssey.")
    params: dict[str, str] = {
        "use_surface_stations": surface_stations,
    }
    if cargo_capacity:
        params["cargo_capacity"] = cargo_capacity
    route_distance = _numberish_string(_payload_string(payload, "max_route_distance_ly"))
    if route_distance:
        params["max_route_distance_ly"] = route_distance
    station_distance = _payload_string(payload, "max_station_distance_ls")
    if station_distance:
        params["max_station_distance_ls"] = _numberish_string(station_distance) or "any"
    min_supply = _numberish_string(_payload_string(payload, "min_supply"))
    if min_supply:
        params["min_supply"] = min_supply
    min_demand = _numberish_string(_payload_string(payload, "min_demand"))
    if min_demand:
        params["min_demand"] = min_demand
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
    use_surface_stations: str,
) -> dict[str, Any]:
    return {
        "system_name": result.system_name,
        "query_url": result.query_url,
        "searched_at": result.searched_at,
        "route_count": len(routes),
        "unfiltered_route_count": unfiltered_count,
        "station_carrier_only": use_surface_stations == "no",
        "use_surface_stations": use_surface_stations,
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
    journal_dir: Path | None,
    peer_link: PeerLink | None,
    route_compare_navroute_wait_seconds: float,
    route_compare_compare_retry_attempts: int,
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
            journal_dir=journal_dir,
            peer_link=peer_link,
            route_compare_navroute_wait_seconds=route_compare_navroute_wait_seconds,
            route_compare_compare_retry_attempts=route_compare_compare_retry_attempts,
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
    journal_dir: Path | None = None,
    peer_link: PeerLink | None = None,
    route_compare_navroute_wait_seconds: float = 6.0,
    route_compare_compare_retry_attempts: int = 3,
) -> dict[str, object] | None:
    if message.get("message_type") == "command.search_haul_routes":
        return await _handle_search_haul_routes_message_async(
            message,
            client_role=client_role,
            data_provider=data_provider,
            peer_link=peer_link,
        )
    if message.get("message_type") == "command.dispatch_route_all_in_one":
        return await _handle_dispatch_route_all_in_one_async(
            message,
            command_handler=command_handler,
            broker=broker,
            journal_dir=journal_dir,
            navroute_wait_seconds_default=route_compare_navroute_wait_seconds,
            compare_retry_attempts_default=route_compare_compare_retry_attempts,
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
            logger.exception("submit_input dispatch failed")
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
            logger.exception("dispatch_destination failed")
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
            manual_landing_value = payload.get("manual_landing", payload.get("on_land"))
            manual_landing = bool(manual_landing_value) if isinstance(manual_landing_value, bool) else False
            command_handler.dispatch_travel(
                system=system.strip(),
                station=station.strip(),
                manual_landing=manual_landing,
                skip_delay=skip_delay,
                raw_command=raw_command,
            )
        except Exception as exc:
            logger.exception("dispatch_travel failed")
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

    if message_type == "command.dispatch_spansh_route":
        if command_handler is None:
            return _transport_unavailable_error(correlation_message_id)
        route_id_value = payload.get("route_id")
        if not isinstance(route_id_value, str) or not route_id_value.strip():
            return protocol_message(
                "response.error",
                {
                    "error_code": "invalid_command",
                    "error_message": "Spansh dispatch commands must include a route_id string.",
                    "recommended_action": "Run route compare first, then pass its route_id.",
                    "retryable": True,
                },
                correlation_message_id=correlation_message_id,
            )
        route = broker.server_state.get_spansh_route(route_id_value.strip())
        if route is None:
            return protocol_message(
                "response.error",
                {
                    "error_code": "invalid_command",
                    "error_message": "Spansh route no longer cached; run Compare again.",
                    "recommended_action": "Re-run route compare and dispatch with the new route_id.",
                    "retryable": True,
                },
                correlation_message_id=correlation_message_id,
            )
        station_value = payload.get("station", "")
        if not isinstance(station_value, str):
            return protocol_message(
                "response.error",
                {
                    "error_code": "invalid_command",
                    "error_message": "Spansh dispatch station must be a string when present.",
                    "recommended_action": "Send station as a string or omit it for system-only travel.",
                    "retryable": True,
                },
                correlation_message_id=correlation_message_id,
            )
        raw_command_value = payload.get("raw_command")
        raw_command = raw_command_value if isinstance(raw_command_value, str) else None
        try:
            skip_delay_value = payload.get("skip_delay")
            skip_delay = bool(skip_delay_value) if isinstance(skip_delay_value, bool) else False
            command_handler.dispatch_spansh_route(
                route=route,
                station=station_value.strip(),
                skip_delay=skip_delay,
                raw_command=raw_command,
            )
        except Exception as exc:
            logger.exception("dispatch_spansh_route failed")
            return _command_execution_failed_error(exc, correlation_message_id)
        broker.server_state.set_active_spansh_route(route_id_value.strip())
        _publish_route_hydrate(broker=broker, data_provider=data_provider)
        return protocol_message(
            "response.success",
            {
                "accepted": True,
                "message_text": "Spansh route dispatch accepted.",
                "result": {
                    "route_id": route_id_value.strip(),
                    "station": station_value.strip(),
                    "destination_system": route.destination_system,
                    "waypoint_count": len(route.waypoints),
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
            logger.exception("dispatch_haul_loop failed")
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
        try:
            search = _haul_search_from_payload(payload, data=data_provider())
            _save_haul_search_defaults(search.query_params)
            result = _run_haul_search(search, peer_link=None)
        except _HaulSearchError as exc:
            return _haul_search_error_response(exc, correlation_message_id)
        return _haul_search_success_response(result, correlation_message_id)

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
            logger.exception("cancel_active_routine failed")
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
