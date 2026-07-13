from __future__ import annotations

import json
import unittest
from pathlib import Path

from edap.routing.types import Route
from edap.routing.web import (
    available_fixtures,
    build_live_comparison,
    comparison_to_payload,
    load_fixture_comparison,
)
from edap.spansh_router import parse_spansh_result

FIXTURES = Path(__file__).parent / "fixtures" / "routing"


class FixtureComparisonTests(unittest.TestCase):
    def test_available_fixtures(self) -> None:
        self.assertIn("hd232819_xinca_normal", available_fixtures())
        self.assertIn("hd232819_xinca_overcharge", available_fixtures())

    def test_normal_fixture_loads_and_shows_in_game_better(self) -> None:
        comparison = load_fixture_comparison("hd232819_xinca_normal")
        self.assertEqual(comparison.verdict, "in_game_better")
        self.assertGreater(comparison.jumps_delta, 0)

    def test_overcharge_fixture_shows_spansh_better(self) -> None:
        comparison = load_fixture_comparison("hd232819_xinca_overcharge")
        self.assertEqual(comparison.verdict, "spansh_better")
        self.assertLess(comparison.jumps_delta, 0)

    def test_unknown_fixture_raises(self) -> None:
        with self.assertRaises(ValueError):
            load_fixture_comparison("nonexistent")

    def test_payload_shape(self) -> None:
        comparison = load_fixture_comparison("hd232819_xinca_overcharge")
        payload = comparison_to_payload(comparison)
        self.assertIn("verdict", payload)
        self.assertIn("jumps_delta", payload)
        self.assertIn("tts_phrase", payload)
        self.assertIn("in_game", payload)
        self.assertIn("spansh", payload)
        self.assertIsInstance(payload["in_game"]["waypoints"], list)
        self.assertGreater(len(payload["in_game"]["waypoints"]), 0)
        self.assertIsInstance(payload["spansh"]["waypoints"], list)
        self.assertEqual(payload["spansh"]["metadata"]["kind"], "spansh")
        self.assertEqual(payload["spansh"]["metadata"]["supercharge_multiplier"], 6)
        self.assertEqual(payload["in_game"]["metadata"]["kind"], "in_game")
        self.assertEqual(payload["in_game"]["source"], "in_game")
        self.assertEqual(payload["spansh"]["source"], "spansh")


class LiveComparisonTests(unittest.TestCase):
    def test_uses_injected_fns(self) -> None:
        with (FIXTURES / "spansh_hd232819_xinca_overcharge_completed.json").open() as fh:
            spansh_payload = json.load(fh)
        stub_spansh = parse_spansh_result(spansh_payload)

        def fake_plot(**kwargs) -> Route:
            self.assertEqual(kwargs["source_system"], "HD 232819")
            self.assertEqual(kwargs["destination_system"], "Xinca")
            self.assertEqual(kwargs["supercharge_multiplier"], 6)
            return stub_spansh

        def fake_read(path: Path) -> Route:
            self.assertEqual(path.name, "NavRoute.json")
            from edap.routing.navroute import read_navroute
            return read_navroute(FIXTURES / "navroute_hd232819_xinca.json")

        comparison = build_live_comparison(
            journal_dir=Path("/imaginary/journal"),
            source_system="HD 232819",
            destination_system="Xinca",
            range_ly=60.0,
            supercharge_multiplier=6,
            plot_route_fn=fake_plot,
            read_navroute_fn=fake_read,
        )
        self.assertEqual(comparison.verdict, "spansh_better")


if __name__ == "__main__":
    unittest.main()
