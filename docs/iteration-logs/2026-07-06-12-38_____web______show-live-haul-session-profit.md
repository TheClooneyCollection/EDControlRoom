# Iteration Log

- Area: `web`
- Title: `show-live-haul-session-profit`
- Started: `2026-07-06 12:38`

## Summary

- Fixed the `/haul` summary profit tile so it shows live haul session profit instead of completed-run-only accumulated profit.

## Changes

- Renamed the summary tile from `Accumulated profit` to `Session profit`.
- Added a `sessionProfit()` frontend helper that calculates `accumulated_profit + current_run_profit`, matching the TUI haul panel and persisted session-profit semantics.
- Left the active routine mini metric as `Current / Accumulated` so operators can still see the current run contribution separately from completed runs.
- Added static web coverage that locks the session-profit calculation into `tests/test_control_room_haul_web.py`.
- Verified `uv run python3 -m unittest tests/test_control_room_haul_web.py` and `uv run python3 -m unittest discover -s tests` passed. The first full-suite report was slow at `690 tests in 0.968s`, then the required timing report passed at `690 tests in 0.387s`.

## Follow-ups

- Live-check the `/haul` tile during an active loop after buy and sell events to confirm the signed current-run contribution matches operator expectations.
