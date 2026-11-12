from __future__ import annotations

from contextlib import redirect_stdout, redirect_stderr
from dataclasses import asdict, FrozenInstanceError
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import unittest

from edcr.haul_history import parse_window, summarize
from tools.haul_stats import main

UTC = timezone.utc
NOW = datetime(2026, 11, 9, 12, tzinfo=UTC)


def run_row(*, status="completed", cost=100, revenue=300, expected=150, duration=1800,
            ended="2026-11-09T10:00:00Z", station="A", tons_bought=10, tons_sold=10):
    return {
        "schema": 1, "kind": "two_way", "status": status,
        "started_at": "2026-11-09T09:00:00Z", "ended_at": ended,
        "route": {"station_1": station, "system_1": "Sol", "station_2": "B", "system_2": "Achenar"},
        "cost": cost, "revenue": revenue, "profit": revenue - cost,
        "expected_profit": expected, "duration_s": duration,
        "legs": [{"buys": [{"commodity": "gold", "tons": tons_bought, "cost": cost}],
                  "sells": [{"commodity": "gold", "tons": tons_sold, "revenue": revenue}]}],
    }


class HaulWindowTests(unittest.TestCase):
    def test_calendar_windows_and_monday_boundary_use_supplied_local_zone(self):
        local = timezone(timedelta(hours=10))
        monday = datetime(2026, 11, 9, 0, 0, tzinfo=local)
        for window, expected in (("", monday), ("today", monday), ("week", monday),
                                 ("month", monday.replace(day=1)),
                                 ("since 2026-11-02", monday.replace(day=2)), ("all", None),
                                 ("48h", monday - timedelta(hours=48)), ("7d", monday - timedelta(days=7)),
                                 ("30d", monday - timedelta(days=30))):
            with self.subTest(window=window):
                since, until, label = parse_window(window, monday)
                self.assertEqual(since, expected)
                self.assertEqual(until, monday)
                self.assertTrue(label)
        sunday = monday - timedelta(seconds=1)
        self.assertEqual(parse_window("week", sunday)[0], monday - timedelta(days=7))

    def test_today_selects_utc_rows_by_local_date_and_ended_at(self):
        local_now = NOW.astimezone(timezone(timedelta(hours=10)))
        since, until, _ = parse_window("today", local_now)
        rows = [run_row(ended="2026-11-08T13:59:59Z"),  # yesterday locally
                run_row(ended="2026-11-08T14:00:00Z"),  # local midnight
                run_row(ended="2026-11-09T12:00:00Z"),  # inclusive now
                run_row(ended="2026-11-09T12:00:01Z")]
        self.assertEqual(summarize(rows, since, until).completed.count, 2)

    def test_calendar_midnight_and_elapsed_48h_across_daylight_saving(self):
        try:
            zone = ZoneInfo("Europe/London")
        except ZoneInfoNotFoundError:
            self.skipTest("IANA timezone data unavailable")
        now = datetime(2026, 10, 25, 12, tzinfo=zone)
        midnight, _, _ = parse_window("today", now)
        self.assertEqual(midnight.utcoffset(), timedelta(hours=1))
        since, _, _ = parse_window("48h", now)
        self.assertEqual(now.timestamp() - since.timestamp(), 48 * 3600)
        self.assertEqual(parse_window("week", now)[0].day, 19)

    def test_system_timezone_adapter_matches_native_conversion_at_each_date(self):
        from edcr.platform.local_time import SystemLocalTimezone
        zone = SystemLocalTimezone()
        # Compare against OS conversion rather than assume the machine's zone.
        for month in (1, 4, 7, 10, 11):
            naive = datetime(2026, month, 25, 0)
            aware = naive.replace(tzinfo=zone)
            self.assertEqual(aware.utcoffset(), naive.astimezone().utcoffset())
            self.assertEqual(aware.tzname(), naive.astimezone().tzname())
            self.assertEqual(datetime.fromtimestamp(aware.timestamp(), zone), aware)

    def test_bad_windows_have_usage_and_reject_naive_clock(self):
        for text in ("year", "since", "since 2026-02-30", "since 2026-1-1", "since 2027-01-01", "all junk"):
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, "Usage: stats"):
                parse_window(text, NOW)
        with self.assertRaisesRegex(ValueError, "timezone"):
            parse_window("today", NOW.replace(tzinfo=None))


class HaulSummaryTests(unittest.TestCase):
    def test_completed_rates_and_expectations_exclude_aborted_runs(self):
        rows = [run_row(), run_row(cost=40, revenue=100, expected=None, tons_bought=4, tons_sold=4),
                run_row(status="aborted", cost=80, revenue=10, expected=500, duration=10000,
                        station="C", tons_bought=8, tons_sold=1)]
        result = summarize(rows, None, NOW, skipped_lines=3)
        self.assertEqual(asdict(result.completed), {
            "count": 2, "cost": 140, "revenue": 400, "profit": 260, "duration_s": 3600,
            "profit_per_hour": 260, "mean_profit": 130, "best_profit": 200,
            "expected_count": 1, "expected_profit": 150, "expected_actual_profit": 200, "profit_delta": 50,
        })
        self.assertEqual(asdict(result.aborted),
                         {"count": 1, "cost": 80, "revenue": 10, "profit": -70, "duration_s": 10000})
        self.assertEqual(asdict(result.all_in),
                         {"count": 3, "cost": 220, "revenue": 410, "profit": 190, "duration_s": 13600})
        # The total covers aborted runs too, since a stop or relaunch splits a run into aborted halves.
        self.assertEqual(result.all_in_duration_s, 13600)
        self.assertAlmostEqual(result.all_in_profit_per_hour, 190 * 3600 / 13600)
        self.assertEqual(result.skipped_lines, 3)
        self.assertEqual(len(result.routes), 2)
        self.assertEqual(result.routes[0].completed.profit, 260)
        # Each route keeps its own haul time, so its profit per hour can be measured.
        self.assertEqual(result.routes[0].completed.duration_s, 3600)
        self.assertEqual(result.routes[1].aborted.profit, -70)
        gold, = result.commodities
        self.assertEqual(asdict(gold.all_in), {"tons_bought": 22, "tons_sold": 15, "cost": 220, "revenue": 410})
        self.assertEqual(gold.completed.tons_bought, 14)
        self.assertEqual(gold.aborted.tons_sold, 1)
        with self.assertRaises(FrozenInstanceError):
            result.skipped_lines = 0
        json.dumps(asdict(result), allow_nan=False)

    def test_empty_zero_duration_negative_profit_and_unknown_expectation(self):
        empty = summarize([], None, NOW)
        self.assertEqual(empty.all_in.count, 0)
        self.assertIsNone(empty.completed.mean_profit)
        self.assertIsNone(empty.completed.best_profit)
        self.assertIsNone(empty.completed.profit_per_hour)
        self.assertIsNone(empty.all_in_profit_per_hour)
        result = summarize([run_row(cost=20, revenue=0, expected=None, duration=0)], None, NOW)
        self.assertEqual(result.completed.best_profit, -20)
        self.assertIsNone(result.completed.profit_per_hour)
        self.assertEqual(result.completed.expected_count, 0)
        self.assertIsNone(result.completed.expected_profit)
        self.assertIsNone(result.completed.expected_actual_profit)
        self.assertIsNone(result.completed.profit_delta)

    def test_invalid_end_timestamp_is_reported_with_reader_skips(self):
        result = summarize([run_row(ended="broken"), run_row(ended="2026-11-09T10:00:00")], None, NOW, skipped_lines=2)
        self.assertEqual(result.skipped_lines, 4)
        self.assertEqual(result.all_in.count, 0)


class HaulStatsCliTests(unittest.TestCase):
    def test_json_uses_same_window_summary_and_reports_invalid_lines(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "runs.jsonl"
            path.write_text(json.dumps(run_row()) + '\n{"torn":', encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                code = main(["since", "2026-11-01", "--json", "--file", str(path), "--journal-dir", directory], now=NOW)
        payload = json.loads(output.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(payload["completed"]["profit"], 200)
        self.assertEqual(payload["skipped_lines"], 1)

    def test_missing_file_has_valid_zero_json_and_bad_window_is_usage_error(self):
        with TemporaryDirectory() as directory:
            output, error = io.StringIO(), io.StringIO()
            with redirect_stdout(output):
                code = main(["--json", "--file", str(Path(directory) / "absent"), "--journal-dir", directory], now=NOW)
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output.getvalue())["all_in"]["count"], 0)
            with redirect_stderr(error):
                code = main(["bad-window"], now=NOW)
            self.assertEqual(code, 2)
            self.assertIn("Usage: stats", error.getvalue())

    def test_text_summary_and_unreadable_file(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "runs.jsonl"
            path.write_text(json.dumps(run_row()) + "\n", encoding="utf-8")
            output, error = io.StringIO(), io.StringIO()
            with redirect_stdout(output):
                code = main(["all", "--file", str(path), "--journal-dir", directory], now=NOW)
            self.assertEqual(code, 0)
            self.assertIn("Total: profit 200 CR", output.getvalue())
            self.assertIn("Completed: 1 runs", output.getvalue())
            self.assertIn("profit 200 CR", output.getvalue())
            with redirect_stderr(error):
                code = main(["--file", directory, "--journal-dir", directory], now=NOW)
            self.assertEqual(code, 2)
            self.assertTrue(error.getvalue())


class TodayHaulCacheTests(unittest.TestCase):
    def test_cache_reads_only_on_start_invalidation_or_local_date_change(self):
        from edcr.haul_stats_cache import TodayHaulCache
        with TemporaryDirectory() as directory:
            path = Path(directory) / "history.jsonl"
            cache = TodayHaulCache()
            self.assertEqual(cache.current(path, now=NOW).count, 0)
            path.write_text(json.dumps(run_row()) + "\n", encoding="utf-8")
            # A changed file is not reread on every rendering pass.
            self.assertEqual(cache.current(path, now=NOW).count, 0)
            cache.invalidate()
            self.assertEqual(cache.current(path, now=NOW).profit, 200)
            self.assertEqual(cache.current(path, now=NOW + timedelta(days=1)).count, 0)
