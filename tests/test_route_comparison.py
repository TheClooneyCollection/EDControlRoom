from __future__ import annotations

import json
import unittest
from pathlib import Path

from edap.routing.comparison import compare
from edap.routing.navroute import read_navroute
from edap.spansh_router import parse_spansh_result

FIXTURES = Path(__file__).parent / "fixtures" / "routing"


def _load_spansh(name: str):
    with (FIXTURES / name).open() as fh:
        return parse_spansh_result(json.load(fh))


class RouteComparisonTests(unittest.TestCase):
    def setUp(self) -> None:
        self.in_game = read_navroute(FIXTURES / "navroute_hd232819_xinca.json")
        self.spansh_normal = _load_spansh("spansh_hd232819_xinca_normal_completed.json")
        self.spansh_overcharge = _load_spansh("spansh_hd232819_xinca_overcharge_completed.json")

    def test_in_game_beats_spansh_normal(self) -> None:
        result = compare(self.in_game, self.spansh_normal)
        self.assertEqual(result.jumps_delta, self.spansh_normal.total_jumps - self.in_game.total_jumps)
        self.assertGreater(result.jumps_delta, 0)
        self.assertEqual(result.verdict, "in_game_better")
        self.assertIn("adds", result.tts_phrase)
        self.assertIn("Commander,", result.tts_phrase)
        self.assertTrue(result.jump_summary.startswith("adds"))
        self.assertIn("neutron jumps", result.neutron_summary)

    def test_spansh_overcharge_beats_in_game(self) -> None:
        result = compare(self.in_game, self.spansh_overcharge)
        self.assertLess(result.jumps_delta, 0)
        self.assertEqual(result.verdict, "spansh_better")
        self.assertIn("saves", result.tts_phrase)

    def test_neutron_delta_and_more_wording(self) -> None:
        result = compare(self.in_game, self.spansh_overcharge)
        expected_delta = self.spansh_overcharge.neutron_count - self.in_game.neutron_count
        self.assertEqual(result.neutron_delta, expected_delta)
        self.assertIn("more neutron jumps", result.tts_phrase)

    def test_custom_title_used_in_phrase(self) -> None:
        result = compare(self.in_game, self.spansh_overcharge, title="CMDR Test")
        self.assertTrue(result.tts_phrase.startswith("CMDR Test, Spansh"))

    def test_even_verdict_and_phrase(self) -> None:
        even_spansh = _load_spansh("spansh_hd232819_xinca_overcharge_completed.json")
        # Fabricate an even comparison by mutating in_game to match spansh totals.
        from dataclasses import replace
        stubbed = replace(
            self.in_game,
            total_jumps=even_spansh.total_jumps,
            neutron_count=even_spansh.neutron_count,
        )
        result = compare(stubbed, even_spansh)
        self.assertEqual(result.verdict, "even")
        self.assertIn("matches on jumps", result.tts_phrase)
        self.assertIn("same number of neutron jumps", result.tts_phrase)

    def test_fewer_neutrons_phrasing(self) -> None:
        # Fabricate a spansh route with fewer neutrons than in-game.
        from dataclasses import replace
        stubbed_in_game = replace(
            self.in_game,
            neutron_count=self.spansh_normal.neutron_count + 3,
        )
        result = compare(stubbed_in_game, self.spansh_normal)
        self.assertEqual(result.neutron_delta, -3)
        self.assertIn("3 fewer neutron jumps", result.tts_phrase)


if __name__ == "__main__":
    unittest.main()
