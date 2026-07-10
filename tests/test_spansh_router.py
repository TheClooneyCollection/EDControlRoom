from __future__ import annotations

import json
import unittest
from pathlib import Path

import httpx

from edap.spansh_router import SpanshRoute, parse_spansh_result, plot_route

FIXTURES = Path(__file__).parent / "fixtures" / "routing"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


class TestParseSpanshResultNormal(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = _load("spansh_hd232819_xinca_normal_completed.json")
        self.route = parse_spansh_result(self.payload)

    def test_waypoint_count(self) -> None:
        self.assertEqual(len(self.route.waypoints), 8)

    def test_total_jumps(self) -> None:
        self.assertEqual(self.route.total_jumps, 32)

    def test_galaxy_map_visits(self) -> None:
        self.assertEqual(self.route.galaxy_map_visits, 7)

    def test_neutron_count(self) -> None:
        self.assertEqual(self.route.neutron_count, 6)

    def test_supercharge_multiplier(self) -> None:
        self.assertEqual(self.route.supercharge_multiplier, 4)

    def test_source_system(self) -> None:
        self.assertEqual(self.route.source_system, "HD 232819")

    def test_destination_system(self) -> None:
        self.assertEqual(self.route.destination_system, "Xinca")

    def test_star_class_none(self) -> None:
        for wp in self.route.waypoints:
            self.assertIsNone(wp.star_class)


class TestParseSpanshResultOvercharge(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = _load("spansh_hd232819_xinca_overcharge_completed.json")
        self.route = parse_spansh_result(self.payload)

    def test_total_jumps(self) -> None:
        self.assertEqual(self.route.total_jumps, 23)

    def test_galaxy_map_visits(self) -> None:
        self.assertEqual(self.route.galaxy_map_visits, 6)

    def test_supercharge_multiplier(self) -> None:
        self.assertEqual(self.route.supercharge_multiplier, 6)


class TestParseSpanshResultQueued(unittest.TestCase):
    def test_raises_value_error(self) -> None:
        payload = _load("spansh_hd232819_xinca_queued.json")
        with self.assertRaises(ValueError):
            parse_spansh_result(payload)


class _MockTransport(httpx.BaseTransport):
    def __init__(self, responses: list[tuple[int, dict]]) -> None:
        self._responses = list(responses)
        self.requests: list[httpx.Request] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        status, body = self._responses.pop(0)
        return httpx.Response(status, json=body)


class TestPlotRouteEndToEnd(unittest.TestCase):
    def setUp(self) -> None:
        self.queued = _load("spansh_hd232819_xinca_queued.json")
        self.completed = _load("spansh_hd232819_xinca_normal_completed.json")

    def _make_transport(self) -> _MockTransport:
        job_id = self.queued["job"]
        return _MockTransport([
            (200, {"job": job_id}),
            (200, self.queued),
            (200, self.completed),
        ])

    def test_returns_spansh_route(self) -> None:
        transport = self._make_transport()
        client = httpx.Client(transport=transport, base_url="http://test")
        route = plot_route(
            source_system="HD 232819",
            destination_system="Xinca",
            range_ly=60.0,
            efficiency=60,
            supercharge_multiplier=4,
            base_url="http://test",
            poll_interval_s=0.0,
            timeout_s=10.0,
            client=client,
        )
        self.assertIsInstance(route, SpanshRoute)
        self.assertEqual(route.total_jumps, 32)
        self.assertEqual(route.galaxy_map_visits, 7)

    def test_post_body_fields(self) -> None:
        transport = self._make_transport()
        client = httpx.Client(transport=transport, base_url="http://test")
        plot_route(
            source_system="HD 232819",
            destination_system="Xinca",
            range_ly=60.0,
            efficiency=60,
            supercharge_multiplier=4,
            base_url="http://test",
            poll_interval_s=0.0,
            timeout_s=10.0,
            client=client,
        )
        post_request = transport.requests[0]
        body = post_request.content.decode()
        self.assertIn("from=HD+232819", body)
        self.assertIn("to=Xinca", body)
        self.assertIn("range=60.0", body)
        self.assertIn("efficiency=60", body)
        self.assertIn("supercharge_multiplier=4", body)


class TestPlotRouteTimeout(unittest.TestCase):
    def test_raises_timeout_error(self) -> None:
        queued = _load("spansh_hd232819_xinca_queued.json")
        job_id = queued["job"]
        transport = _MockTransport([
            (200, {"job": job_id}),
            (200, queued),
            (200, queued),
            (200, queued),
            (200, queued),
            (200, queued),
            (200, queued),
            (200, queued),
            (200, queued),
            (200, queued),
        ])
        client = httpx.Client(transport=transport, base_url="http://test")
        with self.assertRaises(TimeoutError):
            plot_route(
                source_system="HD 232819",
                destination_system="Xinca",
                range_ly=60.0,
                base_url="http://test",
                poll_interval_s=0.0,
                timeout_s=0.0,
                client=client,
            )


if __name__ == "__main__":
    unittest.main()
