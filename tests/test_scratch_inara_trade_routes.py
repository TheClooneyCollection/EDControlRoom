from __future__ import annotations

import unittest

from tools.scratch.scratch_inara_trade_routes import _extract_key_value_pairs, _route_summary


class ScratchInaraTradeRoutesTests(unittest.TestCase):
    def test_extract_key_value_pairs_reads_uppercase_metric_rows(self) -> None:
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

    def test_route_summary_parses_endpoints_and_metrics(self) -> None:
        summary = _route_summary(
            {
                "index": 1,
                "text": "",
                "lines": [
                    "FROM Savitskaya Orbital | TSONGORIS\ue81d\ufe0e",
                    "TO Scully-Power Station | IX\ue81d\ufe0e",
                    "ROUTE DISTANCE 33.08 Ly",
                    "UPDATED 3 hours ago",
                    "PROFIT PER UNIT 45,510 Cr",
                ],
                "links": ["https://inara.cz/elite/"],
            }
        )

        self.assertEqual(summary["from_station"], "Savitskaya Orbital")
        self.assertEqual(summary["from_system"], "TSONGORIS")
        self.assertEqual(summary["to_station"], "Scully-Power Station")
        self.assertEqual(summary["to_system"], "IX")
        self.assertEqual(summary["route_distance"], "33.08 Ly")
        self.assertEqual(summary["updated"], "3 hours ago")
        self.assertEqual(summary["profit_per_unit"], "45,510 Cr")


if __name__ == "__main__":
    unittest.main()
