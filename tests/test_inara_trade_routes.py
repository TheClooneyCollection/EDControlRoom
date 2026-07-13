from __future__ import annotations

import unittest

from edap.inara.trade_routes import (
    _extract_key_value_pairs,
    _emit_debug,
    _row_to_route,
    build_trade_routes_url,
    parse_trade_routes_url,
)


class InaraTradeRoutesTests(unittest.TestCase):
    def test_build_trade_routes_url_uses_default_query_and_system(self) -> None:
        url = build_trade_routes_url("Praea Euq AK-A d25")

        self.assertIn("ps1=Praea+Euq+AK-A+d25", url)
        self.assertIn("pi10=460", url)
        self.assertIn("pi2=500", url)

    def test_build_trade_routes_url_maps_any_station_distance_to_inara_zero(self) -> None:
        url = build_trade_routes_url(
            "Ix",
            query_params={"max_station_distance_ls": "any"},
        )

        self.assertIn("ps1=Ix", url)
        self.assertIn("pi9=0", url)

    def test_parse_trade_routes_url_maps_inara_zero_station_distance_to_any(self) -> None:
        system_name, params = parse_trade_routes_url(
            "https://inara.cz/elite/market-traderoutes/?ps1=Ix&pi9=0"
        )

        self.assertEqual(system_name, "Ix")
        self.assertEqual(params["max_station_distance_ls"], "any")

    def test_extract_key_value_pairs_reads_inline_metric_rows(self) -> None:
        fields = _extract_key_value_pairs(
            [
                "FROM Savitskaya Orbital | TSONGORIS",
                "TO Scully-Power Station | IX",
                "ROUTE DISTANCE 33.08 Ly",
                "DISTANCE ~167 Ly",
                "UPDATED 3 hours ago",
                "PROFIT PER HOUR 88,323,553 Cr",
            ]
        )

        self.assertEqual(fields["ROUTE DISTANCE"], "33.08 Ly")
        self.assertEqual(fields["DISTANCE"], "~167 Ly")
        self.assertEqual(fields["UPDATED"], "3 hours ago")
        self.assertEqual(fields["PROFIT PER HOUR"], "88,323,553 Cr")

    def test_extract_key_value_pairs_maps_profit_aliases(self) -> None:
        fields = _extract_key_value_pairs(
            [
                "PROFIT PER LOAD 17,435,380 Cr",
                "PROFIT/HOUR 88,323,553 Cr",
            ]
        )

        self.assertEqual(fields["PROFIT PER TRIP"], "17,435,380 Cr")
        self.assertEqual(fields["PROFIT PER HOUR"], "88,323,553 Cr")

    def test_emit_debug_forwards_event_and_fields(self) -> None:
        captured: list[tuple[str, dict[str, object]]] = []

        def debug_hook(event: str, **fields: object) -> None:
            captured.append((event, fields))

        _emit_debug(debug_hook, "inara_fetch_start", timeout_seconds=20.0, row_count=0)

        self.assertEqual(
            captured,
            [("inara_fetch_start", {"timeout_seconds": 20.0, "row_count": 0})],
        )

    def test_row_to_route_parses_endpoints_and_metrics(self) -> None:
        route = _row_to_route(
            {
                "index": 1,
                "text": "",
                "lines": [
                    "FROM Savitskaya Orbital | TSONGORIS\ue81d\ufe0e",
                    "BUY",
                    "Silver",
                    "TO Scully-Power Station | IX\ue81d\ufe0e",
                    "ROUTE DISTANCE 33.08 Ly",
                    "DISTANCE ~167 Ly",
                    "UPDATED 3 hours ago",
                    "PROFIT PER UNIT 45,510 Cr",
                ],
                "links": ["https://inara.cz/elite/"],
            }
        )

        self.assertEqual(route.from_station, "Savitskaya Orbital")
        self.assertEqual(route.from_system, "TSONGORIS")
        self.assertEqual(route.to_station, "Scully-Power Station")
        self.assertEqual(route.to_system, "IX")
        self.assertEqual(route.distance_from_system, "~167 Ly")
        self.assertIsNone(route.from_station_distance)
        self.assertIsNone(route.to_station_distance)
        self.assertEqual(route.route_distance, "33.08 Ly")
        self.assertEqual(route.updated, "3 hours ago")
        self.assertEqual(route.profit_per_unit, "45,510 Cr")
        self.assertEqual(route.source_buy_commodity, "Silver")

    def test_row_to_route_parses_return_buy_commodity(self) -> None:
        route = _row_to_route(
            {
                "index": 2,
                "text": "",
                "lines": [
                    "FROM Savitskaya Orbital | TSONGORIS",
                    "BUY",
                    "Beryllium",
                    "SELL",
                    "Bauxite",
                    "TO Nyberg Vision | NJOKUJINUN",
                    "SELL",
                    "Beryllium",
                    "BUY",
                    "Bauxite",
                ],
                "links": [],
            }
        )

        self.assertEqual(route.source_buy_commodity, "Beryllium")
        self.assertEqual(route.target_buy_commodity, "Bauxite")

    def test_row_to_route_parses_live_inara_layout_with_buy_price_rows(self) -> None:
        route = _row_to_route(
            {
                "index": 1,
                "text": "",
                "lines": [
                    "FROM Fontana City | HIP 17597",
                    "TO Stronghold Carrier | HIP 17597",
                    "STATION DISTANCE\t148 Ls",
                    "BUY\tSilver",
                    "BUY PRICE\t3,420 Cr",
                    "SUPPLY\t14,595",
                    "SELL\tRobotics",
                    "SELL PRICE\t2,661 Cr | +639 Cr (31%)",
                    "DEMAND\t5,835,635",
                    "STATION DISTANCE\t215 Ls",
                    "SELL\tSilver",
                    "SELL PRICE\t40,684 Cr | +37,264 Cr (1,089%)",
                    "DEMAND\t522,430",
                    "BUY\tRobotics",
                    "BUY PRICE\t2,022 Cr",
                    "SUPPLY\t7,025",
                    "ROUTE DISTANCE\t0 Ly",
                    "DISTANCE\t~167 Ly",
                    "PROFIT PER LOAD\t17,435,380 Cr",
                    "PROFIT/HOUR\t88,323,553 Cr",
                    "UPDATED\t11 minutes ago",
                    "PROFIT PER UNIT\t37,903 Cr",
                ],
                "links": [],
            }
        )

        self.assertEqual(route.source_buy_commodity, "Silver")
        self.assertEqual(route.target_buy_commodity, "Robotics")
        self.assertEqual(route.from_station_distance, "148 Ls")
        self.assertEqual(route.to_station_distance, "215 Ls")
        self.assertEqual(route.distance_from_system, "~167 Ly")
        self.assertEqual(route.profit_per_unit, "37,903 Cr")
        self.assertEqual(route.profit_per_trip, "17,435,380 Cr")
        self.assertEqual(route.profit_per_hour, "88,323,553 Cr")
        self.assertEqual(route.from_supply, "14,595")
        self.assertEqual(route.from_demand, "5,835,635")
        self.assertEqual(route.to_supply, "7,025")
        self.assertEqual(route.to_demand, "522,430")

if __name__ == "__main__":
    unittest.main()
