# Iteration Log

- Area: `control-room`
- Title: `remote-haul-elapsed-read-model`
- Started: `2026-07-01 12:31`

## Summary

- Fixed connect/serve haul panel time tracking by preventing hydrate/read-model data from exporting server-local monotonic start timestamps.

## Changes

- Updated `LocalControlRoomDataSource` haul copying to compute `session_elapsed_s` and `current_run_elapsed_s` at read time and clear `session_started_at` / `current_run_started_at` from the read model.
- Added dependency and hydrate protocol regressions so remote-safe elapsed values are serialized instead of process-local timer origins.
- Verified `uv run python3 -m unittest tests/test_control_room_dependencies.py tests/test_control_room_data_messages.py tests/test_control_room_client.py` and `uv run python3 -m unittest discover -s tests` (`618` tests, `0.305s`).

## Follow-ups

- Live-check a running `control_room.py serve` + `connect` haul session to confirm elapsed values advance acceptably with the current hydrate/update cadence.
