from __future__ import annotations

import asyncio
import unittest
import warnings
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

warnings.filterwarnings(
    "ignore",
    message=r"Using `httpx` with `starlette\.testclient` is deprecated; install `httpx2` instead\.",
)

from starlette.testclient import TestClient

from edap.config import ConfigError, HubConfig, load_config
from edap.control_room.models import ShipState
from edap.control_room.server.app import _handle_session_message_async, build_observer_server_app
from edap.control_room.server.auth import SharedAccessTokenAuth
from edap.control_room.server.broker import InMemoryObserverSessionBroker
from edap.eddn.game_markets import import_markets
from edap.eddn.route_query import parse_route_query, resolve_route_params
from edap.hub import (
    HubClient, HubMarketPusher, HubRequest, HubResponse, HubStatus, HubUnreachable, ping_hub, run_hub_heartbeat,
)
from edap.inara.trade_routes import TradeRoute, TradeRouteSearchResult
from edap.recent_markets import load_recent_markets, snapshot_entry
from tests.test_eddn import memory_store, prices, save_game_markets

TOKEN = "hub-token"
HUB = HubConfig(url="http://hub.local:8765", token=TOKEN)
NOW = 1794387600.0  # 2026-11-11T09:00:00Z


class FakeClock:
    """Wall-clock seconds that move only when a test calls `advance`."""

    def __init__(self, now: float = NOW) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def pusher_for(client: HubClient, logs: list[str], clock: FakeClock | None = None) -> HubMarketPusher:
    return HubMarketPusher(client=client, log=logs.append, status=HubStatus(client, clock or FakeClock()))


def ship_data(system: str = "Sol", cargo_capacity: int = 784) -> object:
    return SimpleNamespace(ship=ShipState(system=system, cargo_capacity=cargo_capacity))


def server(**options: object):
    options.setdefault("data_provider", ship_data)
    return build_observer_server_app(
        command_handler=None, broker=InMemoryObserverSessionBroker(), auth=SharedAccessTokenAuth(TOKEN), **options
    )


class FakeHub:
    """A transport that records requests and answers from a queue, or raises when it is down."""

    def __init__(self, *responses: HubResponse | Exception) -> None:
        self.responses = list(responses)
        self.requests: list[HubRequest] = []

    def __call__(self, request: HubRequest) -> HubResponse:
        self.requests.append(request)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def client_into(app) -> tuple[TestClient, callable]:
    """A transport that sends hub requests to a real hub app in-process."""
    client = TestClient(app)

    def transport(request: HubRequest) -> HubResponse:
        path = request.url.removeprefix(HUB.url)
        response = client.request(request.method, path, headers=dict(request.headers), params=dict(request.params),
                                  json=request.body)
        return HubResponse(response.status_code, response.json())

    return client, transport


class HubConfigTests(unittest.TestCase):
    def test_no_hub_by_default_and_url_is_validated(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text("", encoding="utf-8")
            hub = load_config(path).hub
            self.assertFalse(hub.enabled)
            self.assertEqual((hub.timeout_s, hub.search_timeout_s, hub.heartbeat_s), (10.0, 180.0, 30.0))

            path.write_text('[hub]\nurl = "http://192.168.1.20:8765/"\ntoken = "t"\n', encoding="utf-8")
            hub = load_config(path).hub
            self.assertEqual((hub.url, hub.token, hub.enabled), ("http://192.168.1.20:8765", "t", True))

            path.write_text('[hub]\nurl = "192.168.1.20"\n', encoding="utf-8")
            with self.assertRaisesRegex(ConfigError, "hub.url"):
                load_config(path)
            path.write_text("[hub]\ntimeout_s = 0\n", encoding="utf-8")
            with self.assertRaisesRegex(ConfigError, "hub.timeout_s"):
                load_config(path)
            path.write_text("[hub]\nheartbeat_s = -1\n", encoding="utf-8")
            with self.assertRaisesRegex(ConfigError, "hub.heartbeat_s"):
                load_config(path)
            path.write_text("[hub]\nheartbeat_s = 5\n", encoding="utf-8")
            self.assertEqual(load_config(path).hub.heartbeat_s, 5.0)


class HubMarketPusherTests(unittest.TestCase):
    def test_pushes_all_at_start_then_only_new_markets_and_everything_again_after_a_failure(self) -> None:
        ok = HubResponse(200, {"results": [{"written": True}]})
        hub = FakeHub(ok, ok, HubUnreachable("timed out"), ok)
        logs: list[str] = []
        pusher = pusher_for(HubClient(HUB, hub), logs)
        stations = lambda request: [entry["station"] for entry in request.body["markets"]]  # noqa: E731

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "recent_markets.json"
            save_game_markets(path, "2026-11-10T14:00:00Z", "2026-11-10T13:00:00Z")
            pusher.push_changes(path)
            save_game_markets(path, "2026-11-10T14:00:00Z", "2026-11-10T13:00:00Z", "2026-11-10T15:00:00Z")
            pusher.push_changes(path)
            pusher.push_changes(path)  # nothing new: no request
            save_game_markets(path, "2026-11-10T14:00:00Z", "2026-11-10T13:00:00Z", "2026-11-10T15:00:00Z",
                              "2026-11-10T16:00:00Z")
            pusher.push_changes(path)
            self.assertTrue(pusher.unsent)
            down = pusher.status.snapshot()
            save_game_markets(path, "2026-11-10T14:00:00Z", "2026-11-10T13:00:00Z", "2026-11-10T15:00:00Z",
                              "2026-11-10T16:00:00Z", "2026-11-10T17:00:00Z")
            pusher.push_changes(path)

        self.assertEqual([stations(request) for request in hub.requests], [
            ["Galileo", "Galileo 1"], ["Galileo 2"], ["Galileo 3"],
            ["Galileo", "Galileo 1", "Galileo 2", "Galileo 3", "Galileo 4"],
        ])
        self.assertFalse(pusher.unsent)
        request = hub.requests[0]
        self.assertEqual((request.method, request.url, request.headers["Authorization"], request.timeout_s),
                         ("POST", "http://hub.local:8765/api/markets", f"Bearer {TOKEN}", 10.0))
        self.assertIn("Hub hub.local:8765 is unreachable: timed out", logs[2])
        self.assertEqual((down["reachable"], down["last_error"], down["resend_pending"]), (False, "timed out", True))
        self.assertEqual(down["last_push"], {"at": "2026-11-11T09:00:00Z", "stations": ["Galileo 3"], "written": 0,
                                             "kept": 0, "error": "timed out"})
        up = pusher.status.snapshot()
        self.assertEqual((up["reachable"], up["last_ok_at"], up["resend_pending"]), (True, "2026-11-11T09:00:00Z", False))
        self.assertEqual((up["last_push"]["written"], up["last_push"]["kept"], up["last_push"]["error"]), (1, 0, None))

    def test_a_refused_push_is_resent(self) -> None:
        hub = FakeHub(HubResponse(503, {"detail": "no EDDN market DB"}), HubResponse(200, {"results": []}))
        logs: list[str] = []
        pusher = pusher_for(HubClient(HUB, hub), logs)
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "recent_markets.json"
            save_game_markets(path, "2026-11-10T14:00:00Z")
            pusher.push_changes(path)
            refused = pusher.status.snapshot()
            # The hub answered, so a refusal does not decide reachability; the heartbeat does.
            self.assertEqual((refused["reachable"], refused["resend_pending"]), (None, True))
            self.assertEqual(refused["last_push"]["error"], "HTTP 503: no EDDN market DB")
            save_game_markets(path, "2026-11-10T14:00:00Z", "2026-11-10T15:00:00Z")
            pusher.push_changes(path)
        self.assertIn("503: no EDDN market DB", logs[0])
        self.assertEqual(len(hub.requests[1].body["markets"]), 2)


class HubServerTests(unittest.TestCase):
    def test_markets_endpoint_writes_newest_wins_and_rejects_bad_payloads(self) -> None:
        store = memory_store()
        self.addCleanup(store.close)
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "recent_markets.json"
            save_game_markets(path, "2026-11-10T14:00:00Z")
            [entry] = [snapshot_entry(market) for market in load_recent_markets(path)]
        stale = {**entry, "timestamp": "2026-11-10T13:00:00Z", "items": []}
        hub = server(import_markets=lambda markets: import_markets(store, markets))
        auth = {"Authorization": f"Bearer {TOKEN}"}

        with TestClient(hub) as client, TestClient(server()) as no_db:
            self.assertEqual(client.post("/api/markets", json={"markets": [entry]}).status_code, 401)
            written = client.post("/api/markets", json={"markets": [entry]}, headers=auth).json()["results"]
            kept = client.post("/api/markets", json={"markets": [stale]}, headers=auth).json()["results"]
            self.assertEqual(client.post("/api/markets", json={"markets": [{"station": "x"}]}, headers=auth).status_code, 400)
            self.assertEqual(client.post("/api/markets", json=[], headers=auth).status_code, 400)
            self.assertEqual(no_db.post("/api/markets", json={"markets": [entry]}, headers=auth).status_code, 503)

        self.assertEqual(written, [{"station": "Galileo", "system": "Sol", "timestamp": "2026-11-10T14:00:00Z", "written": True}])
        self.assertFalse(kept[0]["written"])
        self.assertEqual([row[1] for row in prices(store)], ["gold", "insulatingmembrane"])

    def test_haul_search_endpoint_searches_for_the_callers_ship_without_saving_defaults(self) -> None:
        result = TradeRouteSearchResult(system_name="Shinrarta Dezhra", query_url="https://inara.cz/x", searched_at="",
                                        routes=(TradeRoute(index=1, from_station="A", from_system="Shinrarta Dezhra",
                                                           to_station="B", to_system="Alioth"),))
        auth = {"Authorization": f"Bearer {TOKEN}"}
        with (
            patch("edap.control_room.server.app.search_trade_routes", return_value=result) as inara,
            patch("edap.control_room.server.app.save_haul_search_config") as save_defaults,
            TestClient(server(data_provider=lambda: ship_data(system=""))) as client,
        ):
            response = client.post("/api/haul-search", headers=auth, json={
                "system_name": "Shinrarta Dezhra", "cargo_capacity": "1137", "destination": "Alioth",
                "use_surface_stations": "no",
            })
            missing_origin = client.post("/api/haul-search", headers=auth, json={})
            self.assertEqual(client.post("/api/haul-search", json={}).status_code, 401)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"]["routes"][0]["to_system"], "Alioth")
        self.assertEqual(inara.call_args.args, ("Shinrarta Dezhra",))
        self.assertEqual(inara.call_args.kwargs["query_params"]["cargo_capacity"], "1137")
        save_defaults.assert_not_called()
        self.assertEqual((missing_origin.status_code, missing_origin.json()["error_code"]), (400, "invalid_search"))


class PeerServerTests(unittest.TestCase):
    def test_eddn_routes_and_status_go_to_the_hub_with_this_ships_inputs(self) -> None:
        hub = FakeHub(
            HubResponse(200, {"routes": [], "markets_considered": 3}),
            HubResponse(200, {"enabled": True, "store": {"markets": 3}}),
            HubUnreachable("connection refused"),
        )
        saved = {"max_route_distance_ly": "17.2", "min_supply": "5000", "use_surface_stations": "no"}
        peer = server(data_provider=lambda: ship_data(system="Achenar", cargo_capacity=720), hub=HubClient(HUB, hub))

        with patch("edap.control_room.server.app.load_haul_search_config", return_value=saved), TestClient(peer) as client:
            routes = client.get("/api/eddn-routes", params={"access_token": TOKEN, "jumps": "2", "min_supply": "any"})
            status = client.get("/api/eddn-status", params={"access_token": TOKEN})
            down = client.get("/api/eddn-routes", params={"access_token": TOKEN})

        self.assertEqual(routes.json(), {"routes": [], "markets_considered": 3, "hub": "hub.local:8765"})
        self.assertEqual(hub.requests[0].params, {
            "system": "Achenar", "capacity": "720", "jumps": "2", "laden_jump_range_ly": "17.2", "surface": "no",
            "min_supply": "any",
        })
        self.assertEqual(status.json()["hub"], "hub.local:8765")
        self.assertEqual(down.status_code, 502)
        self.assertEqual(down.json()["detail"], "Hub hub.local:8765 is unreachable: connection refused")

    def test_resolved_params_parse_the_same_on_a_hub_without_defaults(self) -> None:
        saved = {"max_route_distance_ly": "17.2", "min_supply": "5000", "min_landing_pad": "medium",
                 "use_surface_stations": "yes_with_odyssey", "max_price_age_hours": "8", "max_station_distance_ls": "1000"}
        for params in ({}, {"jumps": "2", "pad": "S", "max_age_hours": "any"}, {"view": "global", "system": "Lave"}):
            here = parse_route_query(params, search_defaults=saved, current_system="Sol", cargo_capacity=720)
            resolved = resolve_route_params(params, search_defaults=saved, current_system="Sol", cargo_capacity=720)
            self.assertEqual(parse_route_query(resolved, search_defaults={}, current_system="", cargo_capacity=0), here)

    def test_websocket_haul_search_goes_to_the_hub_and_reports_it_unreachable(self) -> None:
        answer = {"result": {"routes": [], "route_count": 0, "query_url": "https://inara.cz/x"}}
        hub = FakeHub(HubResponse(200, answer), HubUnreachable("timed out"))
        client = HubClient(HUB, hub)

        def search() -> dict[str, object]:
            return asyncio.run(_handle_session_message_async(
                {"message_type": "command.search_haul_routes", "message_id": "m1",
                 "payload": {"max_route_distance_ly": "40 ly", "use_surface_stations": "no"}},
                session_id="s", client_role="active_operator", command_handler=None,
                broker=InMemoryObserverSessionBroker(), data_provider=ship_data, hub=client,
            ))

        with (
            patch("edap.control_room.server.app.search_trade_routes") as inara,
            patch("edap.control_room.server.app.save_haul_search_config") as save_defaults,
        ):
            found = search()
            down = search()

        inara.assert_not_called()
        save_defaults.assert_called()  # the peer's own haul_search.toml still remembers the form
        self.assertEqual(found["payload"]["result"]["hub"], "hub.local:8765")
        self.assertEqual(hub.requests[0].body, {
            "use_surface_stations": "no", "cargo_capacity": "784", "max_route_distance_ly": "40",
            "order_by": "best_profit_per_hour_estimate", "system_name": "Sol", "destination": "",
        })
        self.assertEqual((hub.requests[0].url, hub.requests[0].timeout_s), ("http://hub.local:8765/api/haul-search", 180.0))
        self.assertEqual(down["payload"]["error_code"], "hub_unreachable")
        self.assertIn("Hub hub.local:8765 is unreachable", down["payload"]["error_message"])

    def test_peer_pushes_markets_into_a_real_hub_and_searches_through_it(self) -> None:
        store = memory_store()
        self.addCleanup(store.close)
        result = TradeRouteSearchResult(system_name="Sol", query_url="", searched_at="", routes=())
        hub_client, transport = client_into(server(import_markets=lambda markets: import_markets(store, markets)))
        peer_hub = HubClient(HUB, transport)
        logs: list[str] = []
        with TemporaryDirectory() as tmp, hub_client, patch("edap.control_room.server.app.search_trade_routes",
                                                            return_value=result) as inara:
            path = Path(tmp) / "recent_markets.json"
            save_game_markets(path, "2026-11-10T14:00:00Z")
            pusher_for(peer_hub, logs).push_changes(path)
            with TestClient(server(hub=peer_hub)) as peer:
                response = peer.post("/api/haul-search", headers={"Authorization": f"Bearer {TOKEN}"}, json={})

        self.assertEqual(logs, ["Hub hub.local:8765: pushed Galileo (1 written, 0 already newer)"])
        self.assertEqual(store.counts().markets, 1)
        self.assertEqual(response.json()["result"]["hub"], "hub.local:8765")
        self.assertEqual(inara.call_args.kwargs["query_params"]["cargo_capacity"], "784")


class HubHeartbeatTests(unittest.TestCase):
    def test_heartbeat_pings_every_interval_and_logs_only_when_reachability_changes(self) -> None:
        ok = HubResponse(200, {"status": "ok"})
        hub = FakeHub(ok, ok, HubUnreachable("connection refused"), HubUnreachable("timed out"),
                      HubResponse(401, {"detail": "authentication required"}), ok, ValueError("bad answer"))
        clock = FakeClock()
        status = HubStatus(HubClient(HubConfig(url=HUB.url, token=TOKEN, heartbeat_s=15.0), hub), clock)
        # perf_counter is read before each ping and again only after a 200.
        ticks = iter(float(tick) / 1000 for tick in (0, 42, 100, 112, 200, 300, 400, 500, 507, 600))
        waits: list[float] = []
        logs: list[str] = []
        snapshots: list[dict] = []

        def wait(seconds: float) -> bool:
            waits.append(seconds)
            snapshots.append(status.snapshot())
            clock.advance(seconds)
            return len(waits) == 7

        run_hub_heartbeat(status, perf_counter=lambda: next(ticks), wait=wait, log=logs.append)

        self.assertEqual(logs, [
            "Hub hub.local:8765 reachable (42 ms)",
            "Hub hub.local:8765 unreachable: connection refused",
            "Hub hub.local:8765 reachable (7 ms)",
            "Hub heartbeat error: bad answer",
        ])
        self.assertEqual(waits, [15.0] * 7)
        self.assertEqual([request.url for request in hub.requests], ["http://hub.local:8765/api/hub-ping"] * 7)
        self.assertEqual((hub.requests[0].headers["Authorization"], hub.requests[0].timeout_s), (f"Bearer {TOKEN}", 10.0))
        first, second, down, wrong_token = snapshots[0], snapshots[1], snapshots[3], snapshots[4]
        self.assertEqual((first["reachable"], first["latency_ms"], first["last_ok_at"]), (True, 42.0, "2026-11-11T09:00:00Z"))
        self.assertEqual((second["latency_ms"], second["checked_at"]), (12.0, "2026-11-11T09:00:15Z"))
        self.assertEqual((down["reachable"], down["last_error"], down["last_ok_at"], down["checked_at"]),
                         (False, "timed out", "2026-11-11T09:00:15Z", "2026-11-11T09:00:45Z"))
        self.assertEqual(wrong_token["last_error"], "HTTP 401: authentication required")
        self.assertEqual(snapshots[5]["reachable"], True)

    def test_status_before_the_first_check_is_unknown(self) -> None:
        status = HubStatus(HubClient(HUB, FakeHub()), FakeClock())
        self.assertEqual(status.snapshot(), {
            "configured": True, "host": "hub.local:8765", "url": "http://hub.local:8765", "heartbeat_s": 30.0,
            "reachable": None, "checked_at": None, "last_ok_at": None, "last_error": None, "latency_ms": None,
            "last_push": None, "resend_pending": False,
        })

    def test_hub_status_endpoint_reports_the_peers_view_of_its_hub(self) -> None:
        hub_app_client, transport = client_into(server())
        status = HubStatus(HubClient(HUB, transport), FakeClock())
        logs: list[str] = []
        with hub_app_client, TestClient(server(hub_status=status)) as peer, TestClient(server()) as local:
            ping_hub(status, perf_counter=lambda: 0.0, log=logs.append)
            wrong = HubStatus(HubClient(HubConfig(url=HUB.url, token="nope"), transport), FakeClock())
            ping_hub(wrong, perf_counter=lambda: 0.0, log=logs.append)
            reported = peer.get("/api/hub-status", params={"access_token": TOKEN})
            unauthorized = peer.get("/api/hub-status")
            no_hub = local.get("/api/hub-status", params={"access_token": TOKEN})

        self.assertEqual(logs, ["Hub hub.local:8765 reachable (0 ms)",
                                "Hub hub.local:8765 unreachable: HTTP 401: authentication required"])
        self.assertEqual((reported.json()["reachable"], reported.json()["host"]), (True, "hub.local:8765"))
        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(no_hub.json(), {"configured": False})

    def test_every_page_with_a_sidebar_loads_the_hub_chip(self) -> None:
        with TestClient(server()) as client:
            script = client.get("/assets/hub-status.js")
            pages = {path: client.get(path, params={"access_token": TOKEN}).text
                     for path in ("/haul", "/multi-haul", "/controls", "/markets", "/routes")}
        self.assertIn("/api/hub-status", script.text)
        for path, page in pages.items():
            with self.subTest(path=path):
                self.assertIn('id="hub-chip" hidden', page)
                self.assertIn('src="/assets/hub-status.js"', page)


if __name__ == "__main__":
    unittest.main()
