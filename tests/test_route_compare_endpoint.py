from __future__ import annotations

import unittest
import warnings
from unittest.mock import patch

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

    def test_auth_required(self) -> None:
        with self._client(token="secret") as client:
            response = client.get("/api/spansh-route?from=A&to=B&range=60")
            self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
