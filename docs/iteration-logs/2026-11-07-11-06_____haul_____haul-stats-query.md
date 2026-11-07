# Iteration Log

- Area: `haul`
- Title: `haul-stats-query`
- Started: `2026-11-07 11:06`

## Summary

- Step 2 of haul stats persistence adds a query over `.control_room_haul_runs.jsonl`: the control-room `stats [window]` command and `tools/haul_stats.py`.

## Changes

- `edap/haul_history.py` gains two pure functions:
  - `parse_window(text, now)` handles `today`, `48h`, `week`, `month`, `all` and `since YYYY-MM-DD`. Calendar windows use local time; `48h` is elapsed time. The endpoints are inclusive, and `now` is injected by the caller.
  - `summarize(rows, since, until, *, skipped_lines)` returns a frozen `HaulSummary` that `dataclasses.asdict` can serialize. Rows are assigned to a window by `ended_at`. The summary keeps completed metrics, aborted runs (count and realized profit), an all-in total, and route and commodity breakdowns split by status.
  - Profit/hour, mean, best, and expected vs actual count completed runs only. Expected vs actual uses only the runs that have a known expectation.
- `edap/platform/local_time.SystemLocalTimezone` is a tzinfo that asks the OS for each date's offset, so windows that cross a DST change stay correct without a tz database dependency.
- `stats` is in the dispatch and in the help index, and the web reaches it through `command.submit_input`. `haul_history_summary_lines` in `rendering.py` is shared by the log and the CLI. `tools/haul_stats.py --json` prints the summary as JSON.

## Follow-ups

- Step 3: add a journal trade ledger section to `stats`.
- Step 4: add `/api/haul-stats`, a web History panel, and a one-line TUI summary.
- `tools/haul_stats.py` without `--file` needs `config.toml`. It works in the main checkout but not in a fresh worktree.
