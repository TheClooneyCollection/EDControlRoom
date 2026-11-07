# Iteration Log

- Area: `haul`
- Title: `persist-haul-run-history`
- Started: `2026-11-07 10:56`

## Summary

- Step 1 of the haul stats persistence plan: every two-way haul run is kept as a row in an append-only JSONL file. The user asked that no data be lost, so aborted and interrupted runs are kept with everything captured up to that point.

## Changes

- New `control_room.haul_runs_file`, default `.control_room_haul_runs.jsonl`. It is git-ignored, and `clear` does not touch it.
- `edap/haul_history.py` builds a schema-1 row from the journal events in `handle_haul_event`. A row records:
  - `started_at`/`ended_at` in UTC, taken from journal timestamps;
  - `duration_s` from the live haul clock, which excludes pauses;
  - the route with its systems;
  - per-visit `legs`, with `buys`/`sells` arrays and `market_buy_events`;
  - the raw `events`;
  - `cost`, `revenue`, `profit`, `expected_profit`/`profit_delta`, `top_ups`, `warnings` (IDs of the three haul buy warning TTS messages), `phase` and `reason`.
- The row closes as `completed` in `finalize_completed_haul_run`. It closes as `aborted` on stats stop, clear, a new haul over a stale run, a restart with a saved in-progress run, or the remainder of a resumed mid-run haul (at the ignored station-1 sale, or before the next clean run starts).
- Crash safety:
  - `current_run` and `pending_runs` are saved in `.control_room_state.json`, which is now fsynced.
  - A pending row is removed only after its JSONL append and fsync succeed. A failed append logs a warning and is retried later.
  - `load_runs` skips torn or invalid lines and dedupes on `(started_at, ended_at, station_1)`.
- Behaviour change: haul stats no longer require a station 1 buy commodity, so one-sided loops are tracked and announce the session summary.

## Follow-ups

- Step 2: `stats [today|48h|week|month|since <date>|all]` plus `tools/haul_stats.py`. Windows use local time, and a week starts Monday 00:00. Aborted runs appear on their own line and in an all-in total. Profit/hour and expected vs actual use completed runs only.
- Step 3: a journal trade ledger in `stats`.
- Step 4: `/api/haul-stats`, a web History panel, and a one-line TUI summary.
- Multi-leg runs are not recorded yet.
