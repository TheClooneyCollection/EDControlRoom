from __future__ import annotations

import unittest

from edap.inara.trade_routes import (
    _extract_key_value_pairs,
    _row_to_route,
    build_trade_routes_url,
)


class InaraTradeRoutesTests(unittest.TestCase):
    def test_build_trade_routes_url_uses_default_query_and_system(self) -> None:
        url = build_trade_routes_url("Praea Euq AK-A d25")

        self.assertIn("ps1=Praea+Euq+AK-A+d25", url)
        self.assertIn("pi10=460", url)
        self.assertIn("pi2=60", url)

    def test_extract_key_value_pairs_reads_inline_metric_rows(self) -> None:
        fields = _extract_key_value_pairs(
            [
                "FROM Savitskaya Orbital | TSONGORIS",
                "TO Scully-Power Station | IX",
                "ROUTE DISTANCE 33.08 Ly",
                "UPDATED 3 hours ago",
                "PROFIT PER HOUR 88,323,553 Cr",
            ]
        )

        self.assertEqual(fields["ROUTE DISTANCE"], "33.08 Ly")
        self.assertEqual(fields["UPDATED"], "3 hours ago")
        self.assertEqual(fields["PROFIT PER HOUR"], "88,323,553 Cr")

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
                    "UPDATED\t11 minutes ago",
                    "PROFIT PER UNIT\t37,903 Cr",
                ],
                "links": [],
            }
        )

        self.assertEqual(route.source_buy_commodity, "Silver")
        self.assertEqual(route.target_buy_commodity, "Robotics")
        self.assertEqual(route.profit_per_unit, "37,903 Cr")


if __name__ == "__main__":
    unittest.main()
