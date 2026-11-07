# Iteration Log

- Area: `haul`
- Title: `haul-stats-web-and-backfill`
- Started: `2026-11-07 11:24`

## Summary

- Step 4 of haul stats persistence exposes persisted run history on the web and in the TUI. A one-off journal backfill seeded the run log with this week's hauls.

## Changes

- `GET /api/haul-stats?window=<today|48h|week|month|all|since YYYY-MM-DD>` returns `window`, `label`, `since`, `until`, `runs` (asdict `HaulSummary`) and `journal` (asdict `JournalTradeLedger`, or null without a journal dir or journals).
  - Auth works like other `/api/*` routes. A bad window gives 400, and a read failure gives 503. The read runs in `asyncio.to_thread`.
  - `serve.py` passes `control_room.haul_runs_file`.
- Web Haul v1 gets a History panel with Today/48h/Week/Month/All tabs. The tab choice is remembered in `localStorage`. The panel shows completed metrics, aborted and all-in lines, route and commodity tables, and the journal line. It refreshes on load, on reconnect and when `haul_session.completed_runs` changes.
- The TUI HAUL panel adds `Today +X (n runs)`, read through `edap/haul_stats_cache.TodayHaulCache`. The cache reloads on a local date change or after a successful append, and at state load. It uses persisted rows only, and connect mode shows `Today unavailable`.
- Smoke test against the real backfilled file and journals: `today` 5 runs / 219.13M and `week` 25 + 1 aborted / 844.21M all-in, both matching the journal trade profit.

## Backfill

- `.control_room_haul_runs.jsonl` did not exist before the backfill. It now has 26 rows reconstructed from the 2026-11-05..07 journals: 25 completed and 1 aborted, all from Voltaire Terminal.
- Each row: `source: "journal_backfill"`, `app_version: "backfill"`, `backfill_cutoff: "2026-11-07T11:19:51Z"`, `expected_profit: null`.
- A run spans `Undocked` at station 1 to the station-1 sell after docking back. `duration_s` is in-game time, with gaps between journal files removed (resumed at `LoadGame`).
- A station-1 buy after docking back with no station-1 sale closes the run as `aborted` (the 2026-11-05 session break).
- Totals: profit 844,208,483, which equals the journal trade profit. The reader loads all 26 rows with 0 skipped, and needed no change.
- Cutoff: `2026-11-07T11:19:51Z` is the last journal event backfilled. Hauls after it and before the first server restart with tracking are in neither the backfill nor the live log. Backfill them from later journals using the same cutoff rule.

## Follow-ups

- Land steps 1-4 together, then restart the server once.
- No real browser test of the History panel yet. Only the endpoint and the page markup were checked.
