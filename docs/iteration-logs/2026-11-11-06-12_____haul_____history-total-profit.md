# Iteration Log

- Area: `haul`
- Title: `history-total-profit`
- Started: `2026-11-11 06:12`

## Summary

- Haul history now leads with the all-in Total (profit, time, profit/hour) on the web panel and in `stats` / `tools/haul_stats.py`, instead of completed-only figures.

## Changes

- Why: a stop, pause or relaunch closes the current run as `aborted` and the remainder starts as a `partial_start` run, so one round trip's buy (e.g. -3.96M) and sell (+58.08M) land in two aborted rows. Over the 48h to 2026-11-11 06:00 that was 17 completed runs for 743.5M against 22 aborted for 527.7M: 1.27B all-in at 224M/h vs 211.5M/h completed-only.
- `HaulSummary` gains `all_in_duration_s` and `all_in_profit_per_hour` (summed run durations, so idle gaps between runs are excluded, as for completed). Web metrics are just Total profit, Total / hour, Total time and Runs (`18 done, 22 aborted`), on a 4-column grid (2 on phones); the completed figures, aborted line, expected vs actual, Routes, Commodities and journal sit in a collapsed `Details` that stays open across refreshes once opened. `formatCredits` shows billions with two decimals (1.27b, not 1.3b).

- Total / hour and Total time need a server restart: the fields come from the Python summary, and the running server predates them.

## Follow-ups

- `.control_room_haul_runs.jsonl` has one duplicate run (started 2026-11-09T21:30:19, gold, 24.4M) written twice by 1.26.0 with different `ended_at`, so `load_runs` dedupe misses it; all-in counts it twice.
- The history Routes table can list the same station pair twice (e.g. Chauhan Dock ↔ Sitterly Enterprise 0/2 and 3/3) because rows are grouped by station and system names, and split halves may carry different or missing system names.
