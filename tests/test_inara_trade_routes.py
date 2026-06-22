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


if __name__ == "__main__":
    unittest.main()
