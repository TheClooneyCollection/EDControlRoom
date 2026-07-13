import math
import unittest
from pathlib import Path

from edap.routing.navroute import parse_navroute_json, read_navroute
from edap.routing.types import InGameMetadata

FIXTURE = Path(__file__).parent / "fixtures" / "routing" / "navroute_hd232819_xinca.json"


class TestParseNavrouteFixture(unittest.TestCase):
    def setUp(self):
        self.route = read_navroute(FIXTURE)

    def test_waypoint_count(self):
        self.assertEqual(len(self.route.waypoints), 31)

    def test_total_jumps(self):
        self.assertEqual(self.route.total_jumps, 30)

    def test_neutron_count(self):
        self.assertEqual(self.route.neutron_count, 1)

    def test_timestamp(self):
        assert isinstance(self.route.metadata, InGameMetadata)
        self.assertEqual(self.route.metadata.timestamp, "2026-07-10T17:00:45Z")

    def test_source_tag(self):
        self.assertEqual(self.route.source, "in_game")

    def test_first_waypoint_ly_zero(self):
        first = self.route.waypoints[0]
        self.assertEqual(first.ly_from_prev, 0.0)
        self.assertEqual(first.jumps_from_prev, 0)

    def test_second_waypoint_ly(self):
        p1 = (-1019.09375, -17.15625, -1547.78125)
        p2 = (-998.12500, -37.43750, -1499.09375)
        expected = math.sqrt(sum((b - a) ** 2 for a, b in zip(p1, p2)))
        second = self.route.waypoints[1]
        self.assertAlmostEqual(second.ly_from_prev, expected, places=6)
        self.assertEqual(second.jumps_from_prev, 1)

    def test_neutron_waypoint_flag(self):
        neutrons = [w for w in self.route.waypoints if w.neutron_boost]
        self.assertEqual(len(neutrons), 1)
        self.assertEqual(neutrons[0].system, "Synuefai DW-C d2")


class TestParseNavrouteMalformed(unittest.TestCase):
    def test_missing_route_key(self):
        with self.assertRaises(ValueError):
            parse_navroute_json('{"timestamp": "2026-07-10T17:00:45Z", "event": "NavRoute"}')

    def test_empty_route(self):
        with self.assertRaises(ValueError):
            parse_navroute_json('{"timestamp": "2026-07-10T17:00:45Z", "event": "NavRoute", "Route": []}')

    def test_missing_star_pos(self):
        with self.assertRaises(ValueError):
            parse_navroute_json(
                '{"timestamp": "2026-07-10T17:00:45Z", "event": "NavRoute", "Route": ['
                '{"StarSystem": "Sol", "SystemAddress": 10477373803, "StarClass": "G"}'
                ']}'
            )
