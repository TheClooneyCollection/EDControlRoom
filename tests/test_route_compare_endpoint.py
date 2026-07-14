from __future__ import annotations

import unittest
import warnings
from unittest.mock import patch

import httpx

from edap.routing.types import Route, RouteWaypoint, SpanshMetadata

warnings.filterwarnings(
    "ignore",
    message=r"Using `httpx` with `starlette\.testclient` is deprecated; install `httpx2` instead\.",
)

from starlette.testclient import TestClient

from edap.control_room.server.app import build_observer_server_app
from edap.control_room.server.auth import SharedAccessTokenAuth
from edap.control_room.server.broker import InMemoryObserverSessionBroker


def _stub_data():
    class Stub:
        pass
    return Stub()


def _ws_data():
    # Websocket path reads server_status fields; borrow the fixture from
    # test_control_room_server so the /session handshake works.
    from tests.test_control_room_server import _base_data_read_model
    return _base_data_read_model()


class RouteCompareEndpointTests(unittest.TestCase):
    def _client(self, *, token: str = "test-token", broker: InMemoryObserverSessionBroker | None = None) -> TestClient:
        app = build_observer_server_app(
            data_provider=_stub_data,
            command_handler=None,
            broker=broker or InMemoryObserverSessionBroker(),
            auth=SharedAccessTokenAuth(token),
        )
        return TestClient(app)

    def _get(self, client: TestClient, path: str, *, token: str = "test-token"):
        return client.get(path, headers={"Authorization": f"Bearer {token}"})

    def test_fixture_normal_returns_in_game_better(self) -> None:
        with self._client() as client:
            response = self._get(client, "/api/route-compare?fixture=hd232819_xinca_normal")
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["verdict"], "in_game_better")
            self.assertGreater(payload["jumps_delta"], 0)
            self.assertIn("waypoints", payload["in_game"])
            self.assertIn("waypoints", payload["spansh"])

    def test_fixture_overcharge_returns_spansh_better(self) -> None:
        with self._client() as client:
            response = self._get(client, "/api/route-compare?fixture=hd232819_xinca_overcharge")
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["verdict"], "spansh_better")
            self.assertLess(payload["jumps_delta"], 0)
            self.assertEqual(payload["spansh"]["metadata"]["supercharge_multiplier"], 6)

    def test_unknown_fixture_returns_400(self) -> None:
        with self._client() as client:
            response = self._get(client, "/api/route-compare?fixture=nope")
            self.assertEqual(response.status_code, 400)
            self.assertIn("available_fixtures", response.json())

    def test_missing_params_returns_400(self) -> None:
        with self._client() as client:
            response = self._get(client, "/api/route-compare")
            self.assertEqual(response.status_code, 400)

    def test_live_call_without_journal_dir_returns_503(self) -> None:
        with self._client() as client:
            response = self._get(client, "/api/route-compare?from=A&to=B&range=60")
            self.assertEqual(response.status_code, 503)

    def test_fixture_publishes_spansh_route_ready_announcement(self) -> None:
        broker = InMemoryObserverSessionBroker()
        with self._client(broker=broker) as client:
            response = self._get(client, "/api/route-compare?fixture=hd232819_xinca_overcharge")
            self.assertEqual(response.status_code, 200)
        announcements = broker.server_state.announcements()
        self.assertEqual(len(announcements), 1)
        event = announcements[0]
        self.assertEqual(event.announcement_id, "spansh_route_ready")
        self.assertIn("jump_summary", event.message_values)
        self.assertIn("neutron_summary", event.message_values)
        self.assertIn("Spansh route came back", event.message_text)

    def test_fixture_returns_route_id_and_caches_route(self) -> None:
        broker = InMemoryObserverSessionBroker()
        with self._client(broker=broker) as client:
            response = self._get(client, "/api/route-compare?fixture=hd232819_xinca_overcharge")
        payload = response.json()
        route_id = payload.get("route_id")
        self.assertIsInstance(route_id, str)
        self.assertTrue(route_id)
        cached = broker.server_state.get_spansh_route(route_id)
        self.assertIsNotNone(cached)
        self.assertEqual(cached.source, "spansh")

    def test_auth_required(self) -> None:
        with self._client(token="secret") as client:
            response = client.get("/api/route-compare?fixture=hd232819_xinca_normal")
            self.assertEqual(response.status_code, 401)
            response = client.get(
                "/api/route-compare?fixture=hd232819_xinca_normal",
                headers={"Authorization": "Bearer secret"},
            )
            self.assertEqual(response.status_code, 200)


def _fake_spansh_route(**kwargs) -> Route:
    waypoints = (
        RouteWaypoint(system="Sol", star_class=None, neutron_boost=False, x=0.0, y=0.0, z=0.0, ly_from_prev=0.0, jumps_from_prev=0),
        RouteWaypoint(system="Barnard's Star", star_class=None, neutron_boost=True, x=1.0, y=2.0, z=3.0, ly_from_prev=5.95, jumps_from_prev=1),
    )
    return Route(
        waypoints=waypoints,
        total_ly=5.95,
        total_jumps=1,
        neutron_count=1,
        source="spansh",
        source_system=kwargs.get("source_system", "Sol"),
        destination_system=kwargs.get("destination_system", "Barnard's Star"),
        metadata=SpanshMetadata(
            efficiency=kwargs.get("efficiency", 60),
            supercharge_multiplier=kwargs.get("supercharge_multiplier", 4),
            galaxy_map_visits=0,
        ),
    )


class RouteCompareConfigEndpointTests(unittest.TestCase):
    def _client(
        self,
        *,
        token: str = "test-token",
        navroute_wait_seconds: float = 6.0,
        compare_retry_attempts: int = 3,
    ) -> TestClient:
        app = build_observer_server_app(
            data_provider=_stub_data,
            command_handler=None,
            broker=InMemoryObserverSessionBroker(),
            auth=SharedAccessTokenAuth(token),
            route_compare_navroute_wait_seconds=navroute_wait_seconds,
            route_compare_compare_retry_attempts=compare_retry_attempts,
        )
        return TestClient(app)

    def test_returns_defaults(self) -> None:
        with self._client() as client:
            response = client.get(
                "/api/route-compare/config",
                headers={"Authorization": "Bearer test-token"},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"navroute_wait_seconds": 6.0, "compare_retry_attempts": 3})

    def test_returns_configured_values(self) -> None:
        with self._client(navroute_wait_seconds=9.5, compare_retry_attempts=5) as client:
            response = client.get(
                "/api/route-compare/config",
                headers={"Authorization": "Bearer test-token"},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"navroute_wait_seconds": 9.5, "compare_retry_attempts": 5})

    def test_auth_required(self) -> None:
        with self._client(token="secret") as client:
            response = client.get("/api/route-compare/config")
            self.assertEqual(response.status_code, 401)


class SpanshRouteEndpointTests(unittest.TestCase):
    def _client(self, *, token: str = "test-token", broker: InMemoryObserverSessionBroker | None = None) -> TestClient:
        app = build_observer_server_app(
            data_provider=_stub_data,
            command_handler=None,
            broker=broker or InMemoryObserverSessionBroker(),
            auth=SharedAccessTokenAuth(token),
        )
        return TestClient(app)

    def _get(self, client: TestClient, path: str, *, token: str = "test-token"):
        return client.get(path, headers={"Authorization": f"Bearer {token}"})

    def test_returns_spansh_route_and_caches_id(self) -> None:
        broker = InMemoryObserverSessionBroker()
        with patch("edap.control_room.server.app.plot_route", side_effect=_fake_spansh_route):
            with self._client(broker=broker) as client:
                response = self._get(
                    client,
                    "/api/spansh-route?from=Sol&to=Barnard%27s+Star&range=60&efficiency=60&supercharge_multiplier=4",
                )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("spansh", payload)
        self.assertIn("waypoints", payload["spansh"])
        self.assertEqual(payload["spansh"]["source_system"], "Sol")
        route_id = payload.get("route_id")
        self.assertIsInstance(route_id, str)
        self.assertTrue(route_id)
        cached = broker.server_state.get_spansh_route(route_id)
        self.assertIsNotNone(cached)
        self.assertEqual(cached.destination_system, "Barnard's Star")

    def test_missing_params_returns_400(self) -> None:
        with self._client() as client:
            response = self._get(client, "/api/spansh-route")
            self.assertEqual(response.status_code, 400)

    def test_invalid_numeric_returns_400(self) -> None:
        with self._client() as client:
            response = self._get(client, "/api/spansh-route?from=A&to=B&range=nope")
            self.assertEqual(response.status_code, 400)

    def test_plot_route_failure_returns_502(self) -> None:
        def boom(**_kwargs):
            raise RuntimeError("spansh down")

        with patch("edap.control_room.server.app.plot_route", side_effect=boom):
            with self._client() as client:
                response = self._get(client, "/api/spansh-route?from=A&to=B&range=60")
        self.assertEqual(response.status_code, 502)

    def test_spansh_missing_target_returns_actionable_400(self) -> None:
        request = httpx.Request("POST", "https://spansh.co.uk/api/route")
        response = httpx.Response(
            400,
            request=request,
            json={"error": "Could not find finishing system"},
        )

        with patch(
            "edap.control_room.server.app.plot_route",
            side_effect=httpx.HTTPStatusError("400 Bad Request", request=request, response=response),
        ):
            with self._client() as client:
                result = self._get(client, "/api/spansh-route?from=A&to=B&range=60")

        self.assertEqual(result.status_code, 400)
        self.assertEqual(result.json()["detail"], "Spansh says could not find target system")

    def test_auth_required(self) -> None:
        with self._client(token="secret") as client:
            response = client.get("/api/spansh-route?from=A&to=B&range=60")
            self.assertEqual(response.status_code, 401)


class _FakeCommandHandler:
    def __init__(self) -> None:
        self.dispatched_destinations: list[tuple[str, float, bool, str | None]] = []

    def dispatch_destination(
        self,
        destination: str,
        galaxy_map_settle: float,
        *,
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None:
        self.dispatched_destinations.append((destination, galaxy_map_settle, skip_delay, raw_command))


class DispatchRouteAllInOneTests(unittest.TestCase):
    def _receive_until_response(self, websocket, correlation_id: str):
        for _ in range(16):
            message = websocket.receive_json()
            if message.get("correlation_message_id") == correlation_id:
                return message
        self.fail(f"Did not receive response for {correlation_id}")

    def _client(
        self,
        *,
        broker: InMemoryObserverSessionBroker,
        command_handler: _FakeCommandHandler,
        journal_dir=None,
    ) -> TestClient:
        app = build_observer_server_app(
            data_provider=_ws_data,
            command_handler=command_handler,
            broker=broker,
            auth=SharedAccessTokenAuth("test-token"),
            journal_dir=journal_dir,
            route_compare_navroute_wait_seconds=0.0,
            route_compare_compare_retry_attempts=3,
        )
        return TestClient(app)

    def test_happy_path_dispatches_destination_and_returns_comparison(self) -> None:
        broker = InMemoryObserverSessionBroker()
        handler = _FakeCommandHandler()
        fake_comparison_payload = {
            "verdict": "spansh_better",
            "jumps_delta": -1,
            "neutron_delta": 1,
            "in_game": {"waypoints": [], "total_jumps": 3, "total_ly": 100.0, "neutron_count": 0},
            "spansh": {
                "waypoints": [],
                "total_jumps": 2,
                "total_ly": 100.0,
                "neutron_count": 1,
                "source_system": "Sol",
                "destination_system": "Xinca",
                "metadata": {"efficiency": 60, "supercharge_multiplier": 6, "galaxy_map_visits": 2},
            },
            "route_id": "route-live-123",
        }
        with patch(
            "edap.control_room.server.app.fetch_and_cache_spansh_route",
            return_value=(None, "route-spansh-abc", {"spansh": {"waypoints": [1, 2, 3]}, "route_id": "route-spansh-abc"}),
        ), patch(
            "edap.control_room.server.app.build_and_cache_live_comparison",
            return_value=fake_comparison_payload,
        ):
            with self._client(broker=broker, command_handler=handler) as client:
                with client.websocket_connect("/session?client_name=web&access_token=test-token") as websocket:
                    websocket.receive_json()
                    websocket.receive_json()
                    websocket.send_json({
                        "message_type": "command.dispatch_route_all_in_one",
                        "message_id": "msg-1",
                        "payload": {
                            "from": "Sol",
                            "to": "Xinca",
                            "range": 60,
                            "efficiency": 60,
                            "supercharge_multiplier": 6,
                            "galaxy_map_settle": 1.5,
                            "raw_command": "web all-in-one Sol -> Xinca",
                        },
                    })
                    response = self._receive_until_response(websocket, "msg-1")
        self.assertEqual(response["message_type"], "response.success")
        result = response["payload"]["result"]
        self.assertEqual(result["route_id"], "route-live-123")
        self.assertEqual(result["comparison"]["verdict"], "spansh_better")
        phases = result["phases"]
        self.assertEqual([p["phase"] for p in phases], ["dispatch_destination", "fetch_spansh", "compare"])
        self.assertTrue(all(p["status"] == "ok" for p in phases))
        self.assertEqual(handler.dispatched_destinations, [("Xinca", 1.5, False, "web all-in-one Sol -> Xinca")])

    def test_retries_compare_on_retryable_error_then_succeeds(self) -> None:
        from edap.control_room.server.app import RouteCompareError

        broker = InMemoryObserverSessionBroker()
        handler = _FakeCommandHandler()
        attempts = {"n": 0}

        def compare_side_effect(**_kwargs):
            attempts["n"] += 1
            if attempts["n"] < 3:
                raise RouteCompareError(status_code=404, detail="NavRoute.json not found", retryable=True)
            return {"route_id": "route-final", "verdict": "even", "in_game": {}, "spansh": {}}

        with patch(
            "edap.control_room.server.app.fetch_and_cache_spansh_route",
            return_value=(None, "route-spansh-abc", {"spansh": {"waypoints": []}, "route_id": "route-spansh-abc"}),
        ), patch(
            "edap.control_room.server.app.build_and_cache_live_comparison",
            side_effect=compare_side_effect,
        ):
            with self._client(broker=broker, command_handler=handler) as client:
                with client.websocket_connect("/session?client_name=web&access_token=test-token") as websocket:
                    websocket.receive_json()
                    websocket.receive_json()
                    websocket.send_json({
                        "message_type": "command.dispatch_route_all_in_one",
                        "message_id": "msg-2",
                        "payload": {
                            "from": "Sol",
                            "to": "Xinca",
                            "range": 60,
                            "galaxy_map_settle": 0.5,
                        },
                    })
                    response = self._receive_until_response(websocket, "msg-2")
        self.assertEqual(response["message_type"], "response.success")
        self.assertEqual(attempts["n"], 3)
        phases = response["payload"]["result"]["phases"]
        compare_phases = [p for p in phases if p["phase"] == "compare"]
        self.assertEqual([p["status"] for p in compare_phases], ["retryable", "retryable", "ok"])

    def test_returns_error_when_all_compare_attempts_fail(self) -> None:
        from edap.control_room.server.app import RouteCompareError

        broker = InMemoryObserverSessionBroker()
        handler = _FakeCommandHandler()
        with patch(
            "edap.control_room.server.app.fetch_and_cache_spansh_route",
            return_value=(None, "route-spansh", {"spansh": {"waypoints": []}, "route_id": "route-spansh"}),
        ), patch(
            "edap.control_room.server.app.build_and_cache_live_comparison",
            side_effect=RouteCompareError(status_code=404, detail="NavRoute.json not found", retryable=True),
        ):
            with self._client(broker=broker, command_handler=handler) as client:
                with client.websocket_connect("/session?client_name=web&access_token=test-token") as websocket:
                    websocket.receive_json()
                    websocket.receive_json()
                    websocket.send_json({
                        "message_type": "command.dispatch_route_all_in_one",
                        "message_id": "msg-3",
                        "payload": {"from": "Sol", "to": "Xinca", "range": 60, "galaxy_map_settle": 0.0},
                    })
                    response = self._receive_until_response(websocket, "msg-3")
        self.assertEqual(response["message_type"], "response.error")
        self.assertEqual(response["payload"]["error_code"], "route_all_in_one_compare_failed")

    def test_missing_from_returns_invalid_command(self) -> None:
        broker = InMemoryObserverSessionBroker()
        handler = _FakeCommandHandler()
        with self._client(broker=broker, command_handler=handler) as client:
            with client.websocket_connect("/session?client_name=web&access_token=test-token") as websocket:
                websocket.receive_json()
                websocket.receive_json()
                websocket.send_json({
                    "message_type": "command.dispatch_route_all_in_one",
                    "message_id": "msg-4",
                    "payload": {"to": "Xinca", "range": 60, "galaxy_map_settle": 0.0},
                })
                response = self._receive_until_response(websocket, "msg-4")
        self.assertEqual(response["payload"]["error_code"], "invalid_command")
        self.assertEqual(handler.dispatched_destinations, [])

    def test_no_command_handler_returns_transport_unavailable(self) -> None:
        broker = InMemoryObserverSessionBroker()
        app = build_observer_server_app(
            data_provider=_ws_data,
            command_handler=None,
            broker=broker,
            auth=SharedAccessTokenAuth("test-token"),
            route_compare_navroute_wait_seconds=0.0,
            route_compare_compare_retry_attempts=1,
        )
        with TestClient(app) as client:
            with client.websocket_connect("/session?client_name=web&access_token=test-token") as websocket:
                websocket.receive_json()
                websocket.receive_json()
                websocket.send_json({
                    "message_type": "command.dispatch_route_all_in_one",
                    "message_id": "msg-5",
                    "payload": {"from": "Sol", "to": "Xinca", "range": 60, "galaxy_map_settle": 0.0},
                })
                for _ in range(8):
                    message = websocket.receive_json()
                    if message.get("correlation_message_id") == "msg-5":
                        break
                else:
                    self.fail("no response")
        self.assertEqual(message["payload"]["error_code"], "active_operator_transport_unavailable")


class ActiveSpanshRouteHydrateTests(unittest.TestCase):
    def test_hydrate_omits_active_route_when_none(self) -> None:
        broker = InMemoryObserverSessionBroker()
        app = build_observer_server_app(
            data_provider=_ws_data,
            command_handler=None,
            broker=broker,
            auth=SharedAccessTokenAuth("test-token"),
        )
        with TestClient(app) as client:
            response = client.get(
                "/hydrate",
                headers={"Authorization": "Bearer test-token"},
            )
        self.assertEqual(response.status_code, 200)
        payload = response.json()["payload"]
        self.assertIsNone(payload.get("active_spansh_route"))

    def test_dispatch_spansh_route_sets_active_and_hydrate_exposes_it(self) -> None:
        from edap.routing.route_cache import RouteRequestKey

        broker = InMemoryObserverSessionBroker()

        class _RecordingHandler:
            def __init__(self) -> None:
                self.calls = 0

            def dispatch_spansh_route(self, **_kwargs) -> None:
                self.calls += 1

        handler = _RecordingHandler()
        route = _fake_spansh_route(source_system="Sol", destination_system="Xinca")
        route_id = broker.server_state.cache_spansh_route(
            route,
            request_key=RouteRequestKey(
                source_system="Sol",
                destination_system="Xinca",
                range_ly=60.0,
                efficiency=60,
                supercharge_multiplier=4,
            ),
        )
        app = build_observer_server_app(
            data_provider=_ws_data,
            command_handler=handler,
            broker=broker,
            auth=SharedAccessTokenAuth("test-token"),
        )
        with TestClient(app) as client:
            with client.websocket_connect("/session?client_name=web&access_token=test-token") as websocket:
                websocket.receive_json()  # connection_ready
                websocket.receive_json()  # initial hydrate
                websocket.send_json({
                    "message_type": "command.dispatch_spansh_route",
                    "message_id": "msg-active-1",
                    "payload": {"route_id": route_id, "station": ""},
                })
                messages = []
                for _ in range(6):
                    messages.append(websocket.receive_json())
                    if any(m.get("correlation_message_id") == "msg-active-1" for m in messages):
                        break

        self.assertEqual(handler.calls, 1)
        self.assertEqual(broker.server_state.active_spansh_route_id(), route_id)

        with TestClient(app) as client:
            response = client.get(
                "/hydrate",
                headers={"Authorization": "Bearer test-token"},
            )
        payload = response.json()["payload"]
        active = payload.get("active_spansh_route")
        self.assertIsNotNone(active)
        self.assertEqual(active["route_id"], route_id)
        self.assertEqual(active["route"]["destination_system"], "Xinca")
        waypoints = active["route"]["waypoints"]
        self.assertEqual([w["system"] for w in waypoints], ["Sol", "Barnard's Star"])


if __name__ == "__main__":
    unittest.main()
