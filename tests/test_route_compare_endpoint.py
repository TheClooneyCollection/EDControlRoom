from __future__ import annotations

import unittest
import warnings

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
    def _client(self, *, token: str = "test-token") -> TestClient:
        app = build_observer_server_app(
            data_provider=_stub_data,
            command_handler=None,
            broker=InMemoryObserverSessionBroker(),
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
            self.assertEqual(payload["spansh"]["supercharge_multiplier"], 6)

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

    def test_auth_required(self) -> None:
        with self._client(token="secret") as client:
            response = client.get("/api/route-compare?fixture=hd232819_xinca_normal")
            self.assertEqual(response.status_code, 401)
            response = client.get(
                "/api/route-compare?fixture=hd232819_xinca_normal",
                headers={"Authorization": "Bearer secret"},
            )
            self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
