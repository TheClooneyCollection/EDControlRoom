from contextlib import redirect_stdout
from dataclasses import asdict, FrozenInstanceError
from datetime import datetime, timezone
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from edcr.journal_trade_ledger import journal_trade_ledger
from edcr.control_room.rendering import journal_ledger_lines
from tools.haul_stats import main

SINCE = datetime(2026, 11, 9, tzinfo=timezone.utc)
UNTIL = datetime(2026, 11, 9, 1, tzinfo=timezone.utc)


def event(name, stamp, **values):
    return dict(event=name, timestamp=stamp, **values)


def write_journal(directory, stamp, events):
    path = directory / f"Journal.{stamp}.01.log"
    path.write_text("".join(json.dumps(item) + "\n" for item in events), encoding="utf-8")
    return path


class JournalLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def test_window_spanning_file_boundary_preserves_context_and_observed_balances(self):
        # This older file must not be scanned; it is not the last before since.
        (self.directory / "Journal.2026-11-07T000000.01.log").write_bytes(b"not json\n")
        write_journal(self.directory, "2026-11-08T235900", [
            event("LoadGame", "2026-11-08T23:59:50Z", Credits=1000),
            event("Docked", "2026-11-08T23:59:51Z", StationName="Alpha", MarketID=1),
            event("MarketBuy", "2026-11-08T23:59:59Z", Type="gold", Count=1, TotalCost=10000, MarketID=1),
            event("MarketBuy", "2026-11-09T00:00:01Z", Type="gold", Count=10, TotalCost=100, MarketID=1),
        ])
        second = write_journal(self.directory, "2026-11-09T003000", [
            event("Docked", "2026-11-09T00:30:00Z", StationName="Beta", MarketID=2),
            event("MarketSell", "2026-11-09T00:31:00Z", Type="gold", Count=10, TotalSale=250, AvgPricePaid=10, MarketID=2),
            event("Undocked", "2026-11-09T00:32:00Z"),
            event("MarketBuy", "2026-11-09T00:33:00Z", Type="silver", Count=1, TotalCost=20, MarketID=999),
            event("Location", "2026-11-09T00:33:30Z", StationName="Gamma", MarketID=3),
            event("MarketSell", "2026-11-09T00:34:00Z", Type="silver", Count=1, TotalSale=30, AvgPricePaid=20, MarketID=3),
            event("LoadGame", "2026-11-09T00:40:00Z", Credits=1500),
            event("MarketBuy", "2026-11-09T01:00:01Z", Type="gold", Count=1, TotalCost=999, MarketID=2),
        ])
        with second.open("ab") as handle:
            handle.write(b'{"torn":\n\xff\n')
        (self.directory / "Journal.2026-11-10T000000.01.log").write_bytes(b"not json\n")
        (self.directory / "Status.json").write_text(json.dumps(event("Status", "2026-11-09T00:50:00Z", Balance=1600)))
        result = journal_trade_ledger(self.directory, SINCE, UNTIL)
        self.assertTrue(result.available)
        self.assertEqual((result.buys, result.sells, result.cost, result.revenue, result.profit), (2, 2, 120, 280, 160))
        self.assertEqual(result.sell_margin, 160)
        self.assertEqual((result.start_balance, result.end_balance, result.net_balance_change), (1000, 1600, 600))
        self.assertEqual(result.start_balance_at, "2026-11-08T23:59:50+00:00")
        self.assertEqual(result.coverage.files, 2)
        self.assertEqual(result.coverage.skipped_lines, 2)
        self.assertEqual(result.coverage.first_event_at, "2026-11-08T23:59:50+00:00")
        self.assertEqual(result.coverage.last_event_at, "2026-11-09T01:00:01+00:00")
        stations = {item.station: item for item in result.stations}
        self.assertEqual(stations["Alpha"].cost, 100)
        self.assertEqual(stations["Beta"].revenue, 250)
        self.assertEqual(stations["unknown"].cost, 20)
        self.assertEqual(stations["Gamma"].revenue, 30)
        gold = result.commodities[0]
        self.assertEqual((gold.commodity, gold.tons_bought, gold.tons_sold, gold.sell_margin), ("gold", 10, 10, 150))
        json.dumps(asdict(result))
        with self.assertRaises(FrozenInstanceError):
            result.cost = 0

    def test_missing_or_unreadable_directory_is_one_dim_line(self):
        for directory in (None, self.directory / "missing"):
            result = journal_trade_ledger(directory, SINCE, UNTIL)
            self.assertFalse(result.available)
            lines = journal_ledger_lines(result)
            self.assertEqual(len(lines), 1)
            self.assertTrue(lines[0].startswith("[dim]All trading (journal): unavailable"))
        file = self.directory / "not-directory"
        file.write_text("")
        self.assertFalse(journal_trade_ledger(file, SINCE, UNTIL).available)

    def test_partial_coverage_unknown_basis_and_future_status_are_not_guessed(self):
        write_journal(self.directory, "2026-11-09T001000", [
            event("LoadGame", "2026-11-09T00:10:00Z", Credits=1000),
            event("Docked", "2026-11-09T00:10:01Z", StationName="Alpha"),
            event("MarketSell", "2026-11-09T00:11:00Z", Type="gold", Count=2, TotalSale=50, MarketID=1),
            event("Undocked", "2026-11-09T00:12:00Z"),
            event("MarketBuy", "2026-11-09T00:13:00Z", Type="gold", Count=1, TotalCost=10),
        ])
        (self.directory / "Status.json").write_text(json.dumps(event("Status", "2026-11-09T02:00:00Z", Balance=2000)))
        result = journal_trade_ledger(self.directory, SINCE, UNTIL)
        self.assertIsNone(result.net_balance_change)
        self.assertIsNone(result.sell_margin)
        self.assertIsNone(result.commodities[0].sell_margin)
        self.assertTrue(result.coverage.window_start_before_oldest_journal)
        self.assertEqual(result.stations[0].station, "unknown")

    def test_other_flows_and_balance_samples_are_separate_from_trade_profit(self):
        write_journal(self.directory, "2026-11-09T000000", [
            event("LoadGame", "2026-11-09T00:00:00Z", Credits=1000),
            event("ModuleBuy", "2026-11-09T00:01:00Z", BuyPrice=100, SellPrice=40),
            event("MissionCompleted", "2026-11-09T00:02:00Z", Reward=500),
            event("RepairAll", "2026-11-09T00:03:00Z", Cost=20),
            event("Status", "2026-11-09T01:00:00Z", Balance=1420),
        ])
        result = journal_trade_ledger(self.directory, SINCE, UNTIL)
        self.assertEqual(result.other_flows, {"ModuleBuy": -60, "MissionCompleted": 500, "RepairAll": -20})
        self.assertEqual(result.profit, 0)
        self.assertEqual(result.net_balance_change, 420)

    def test_cli_json_and_text_include_manual_trades_without_run_history(self):
        write_journal(self.directory, "2026-11-09T000000", [
            event("MarketSell", "2026-11-09T00:01:00Z", Type="gold", Count=5, TotalSale=100, AvgPricePaid=10),
        ])
        args = ["all", "--file", str(self.directory / "absent.jsonl"), "--journal-dir", str(self.directory)]
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(args + ["--json"], now=UNTIL), 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["all_in"]["count"], 0)
        self.assertEqual(payload["journal"]["sell_margin"], 50)
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(args, now=UNTIL), 0)
        self.assertIn("All trading (journal)", output.getvalue())
        self.assertIn("gold 50 CR", output.getvalue())

    def test_rendering_limits_top_commodities_to_five(self):
        write_journal(self.directory, "2026-11-09T000000", [
            event("MarketSell", "2026-11-09T00:01:00Z", Type=f"item{n}", Count=1, TotalSale=n, AvgPricePaid=0)
            for n in range(7)
        ])
        lines = journal_ledger_lines(journal_trade_ledger(self.directory, SINCE, UNTIL))
        self.assertIn("item6 6 CR", lines[3])
        self.assertNotIn("item1", lines[3])
        self.assertEqual(len(lines), 5)

    def test_last_balance_before_window_and_market_mapping_survive_undocking(self):
        write_journal(self.directory, "2026-11-08T230000", [
            event("LoadGame", "2026-11-08T23:00:00Z", Credits=100),
            event("LoadGame", "2026-11-08T23:59:00Z", Credits=200),
            event("Docked", "2026-11-08T23:59:01Z", StationName="Alpha", MarketID=7),
            event("Undocked", "2026-11-08T23:59:02Z"),
            event("MarketBuy", "2026-11-09T00:00:00Z", Type="gold", Count=1, TotalCost=10, MarketID=7),
            event("LoadGame", "2026-11-09T01:00:00Z", Credits=190),
        ])
        result = journal_trade_ledger(self.directory, SINCE, UNTIL)
        self.assertEqual(result.start_balance, 200)
        self.assertEqual(result.net_balance_change, -10)
        self.assertEqual(result.stations[0].station, "Alpha")
        self.assertEqual(result.buys, 1)

    def test_empty_directory_and_malformed_trade_are_nonfatal(self):
        empty = journal_trade_ledger(self.directory, SINCE, UNTIL)
        self.assertTrue(empty.available)
        self.assertEqual(empty.coverage.files, 0)
        self.assertIsNone(empty.net_balance_change)
        path = write_journal(self.directory, "2026-11-09T000000", [
            event("MarketBuy", "2026-11-09T00:01:00Z", Type="gold", Count="bad", TotalCost=100),
            event("MarketSell", "bad timestamp", Type="gold", Count=1, TotalSale=100),
        ])
        with path.open("a") as handle:
            handle.write('[]\n')
        result = journal_trade_ledger(self.directory, SINCE, UNTIL)
        self.assertEqual(result.coverage.skipped_lines, 3)
        self.assertEqual((result.buys, result.sells), (0, 0))

    def test_snapshots_entirely_before_window_do_not_imply_window_balance_change(self):
        write_journal(self.directory, "2026-11-08T230000", [
            event("LoadGame", "2026-11-08T23:00:00Z", Credits=100),
        ])
        (self.directory / "Status.json").write_text(json.dumps(
            event("Status", "2026-11-08T23:59:00Z", Balance=200)))
        result = journal_trade_ledger(self.directory, SINCE, UNTIL)
        self.assertIsNone(result.net_balance_change)
