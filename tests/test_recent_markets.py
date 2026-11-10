from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from edap.market_compare import compare_markets
from edap.recent_markets import (
    commodity_key,
    load_recent_markets,
    market_items,
    record_market_json,
)


def market_json(market_id: int, station: str, timestamp: str, items: list[dict] | None = None) -> dict:
    return {
        "timestamp": timestamp,
        "event": "Market",
        "MarketID": market_id,
        "StationName": station,
        "StationType": "Coriolis",
        "StarSystem": f"{station} System",
        "Items": items if items is not None else [],
    }


def item(name: str, localised: str, *, buy: int = 0, sell: int = 0, stock: int = 0, demand: int = 0) -> dict:
    return {
        "Name": f"${name}_name;",
        "Name_Localised": localised,
        "Category_Localised": "Metals",
        "BuyPrice": buy,
        "SellPrice": sell,
        "MeanPrice": 1000,
        "StockBracket": 2 if stock else 0,
        "DemandBracket": 2 if demand else 0,
        "Stock": stock,
        "Demand": demand,
    }


class RecentMarketsStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.path = Path(self.tmpdir.name) / "recent markets.json"
        self.logs: list[str] = []

    def record(self, data: dict) -> bool:
        return record_market_json(self.path, data, self.logs.append)

    def test_visits_keep_newest_first_and_a_revisit_moves_the_station_to_the_top(self) -> None:
        self.assertTrue(self.record(market_json(1, "Alpha", "2026-11-10T10:00:00Z", [item("gold", "Gold", buy=9000)])))
        self.assertTrue(self.record(market_json(2, "Beta", "2026-11-10T11:00:00Z")))
        self.assertTrue(self.record(market_json(1, "Alpha", "2026-11-10T12:00:00Z", [item("gold", "Gold", buy=9500)])))

        markets = load_recent_markets(self.path)

        self.assertEqual([m.station for m in markets], ["Alpha", "Beta"])
        self.assertEqual(markets[0].items[0]["BuyPrice"], 9500)
        self.assertEqual(markets[0].station_type, "Coriolis")
        self.assertEqual(markets[0].system, "Alpha System")
        self.assertEqual(self.logs, [])

    def test_seeding_the_same_or_an_older_market_file_changes_nothing(self) -> None:
        self.record(market_json(1, "Alpha", "2026-11-10T12:00:00Z"))
        before = self.path.read_text(encoding="utf-8")

        self.assertFalse(self.record(market_json(1, "Alpha", "2026-11-10T12:00:00Z")))
        self.assertFalse(self.record(market_json(1, "Alpha", "2026-11-10T09:00:00Z")))
        self.assertEqual(self.path.read_text(encoding="utf-8"), before)

    def test_only_the_ten_most_recent_stations_are_kept(self) -> None:
        for index in range(12):
            self.record(market_json(index, f"Station {index}", f"2026-11-10T{index:02d}:00:00Z"))

        markets = load_recent_markets(self.path)

        self.assertEqual(len(markets), 10)
        self.assertEqual(markets[0].station, "Station 11")
        self.assertEqual(markets[-1].station, "Station 2")

    def test_a_corrupt_store_reads_as_empty_and_is_replaced_by_the_next_visit(self) -> None:
        self.path.write_text("{not json", encoding="utf-8")
        self.assertEqual(load_recent_markets(self.path), ())

        self.record(market_json(3, "Gamma", "2026-11-10T12:00:00Z"))

        self.assertEqual([m.station for m in load_recent_markets(self.path)], ["Gamma"])
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8"))["schema"], 1)
        self.assertEqual(list(Path(self.tmpdir.name).glob("*.tmp")), [])

    def test_a_market_file_without_a_market_id_is_ignored(self) -> None:
        self.assertFalse(self.record({"StationName": "Nowhere", "Items": []}))
        self.assertFalse(self.path.exists())

    def test_a_failed_save_is_logged(self) -> None:
        blocker = Path(self.tmpdir.name) / "file"
        blocker.write_text("", encoding="utf-8")

        changed = record_market_json(blocker / "store.json", market_json(1, "Alpha", "2026-11-10T12:00:00Z"),
                                     self.logs.append)

        self.assertFalse(changed)
        self.assertIn("failed to save recent markets", self.logs[0])

    def test_items_use_the_localised_name_and_the_normalised_internal_key(self) -> None:
        self.record(market_json(1, "Alpha", "2026-11-10T12:00:00Z", [
            item("hazardousenvironmentsuits", "H.E. Suits", buy=200, stock=50),
            {"Name": "$lowtemperaturediamond_name;", "BuyPrice": 0, "SellPrice": 200000, "Demand": 30},
        ]))

        rows = market_items(load_recent_markets(self.path)[0])

        self.assertEqual([row.commodity for row in rows], ["hazardousenvironmentsuits", "lowtemperaturediamond"])
        self.assertEqual(rows[0].name, "H.E. Suits")
        self.assertEqual(rows[0].category, "Metals")
        self.assertEqual((rows[0].buy_price, rows[0].stock, rows[0].mean_price), (200, 50, 1000))
        self.assertEqual(rows[1].name, "lowtemperaturediamond")
        self.assertEqual(rows[1].demand, 30)
        self.assertEqual(commodity_key(" $Gold_Name; "), "gold")


class MarketCompareTests(unittest.TestCase):
    def snapshot_items(self, *items: dict) -> tuple:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "store.json"
            record_market_json(path, market_json(1, "Any", "2026-11-10T12:00:00Z", list(items)), lambda _: None)
            return market_items(load_recent_markets(path)[0])

    def test_deals_rank_by_full_hold_profit_so_a_thin_market_does_not_win(self) -> None:
        market_x = self.snapshot_items(
            item("gold", "Gold", buy=9000, sell=8900, stock=1000),
            item("silver", "Silver", buy=4000, sell=3900, stock=100),
            item("tea", "Tea", buy=1500, sell=1400, stock=0),
            item("beer", "Beer", buy=200, sell=150, stock=500),
            item("robotics", "Robotics", sell=2500, demand=900),
        )
        market_y = self.snapshot_items(
            item("gold", "Or", sell=10000, demand=300),
            item("silver", "Argent", sell=5500, demand=50),
            item("tea", "Tea", sell=9999, demand=10),
            item("beer", "Beer", sell=100, demand=10),
            item("robotics", "Robotics", buy=1500, stock=2000),
        )

        comparison = compare_markets(market_x, market_y, 400)

        self.assertEqual([deal.name for deal in comparison.outbound], ["Gold", "Silver"])
        gold, silver = comparison.outbound
        self.assertEqual((silver.profit_per_ton, silver.hold_tons, silver.hold_profit), (1500, 100, 150000))
        self.assertEqual((gold.buy_price, gold.stock, gold.sell_price, gold.demand), (9000, 1000, 10000, 300))
        self.assertEqual((gold.hold_tons, gold.hold_profit), (400, 400000))
        self.assertEqual([(deal.name, deal.profit_per_ton) for deal in comparison.inbound], [("Robotics", 1000)])
        self.assertEqual(comparison.round_trip.outbound, gold)
        self.assertEqual(comparison.round_trip.profit_per_ton, 1000 + 1000)
        self.assertEqual(comparison.round_trip.hold_profit, 400000 + 1000 * 400)

    def test_a_one_way_market_pair_has_no_return_leg(self) -> None:
        market_x = self.snapshot_items(item("gold", "Gold", buy=9000, stock=10))
        market_y = self.snapshot_items(item("gold", "Gold", sell=9100, demand=5))

        comparison = compare_markets(market_x, market_y, 0)

        self.assertEqual(comparison.inbound, ())
        self.assertIsNone(comparison.round_trip.inbound)
        self.assertEqual(comparison.round_trip.profit_per_ton, 100)
        self.assertEqual(comparison.round_trip.hold_profit, 0)


if __name__ == "__main__":
    unittest.main()
