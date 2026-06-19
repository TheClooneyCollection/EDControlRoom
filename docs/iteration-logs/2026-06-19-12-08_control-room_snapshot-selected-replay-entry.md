# Iteration Log

- Area: `control-room`
- Title: `snapshot-selected-replay-entry`
- Started: `2026-06-19 12:08`

## Summary

- Added replay-browser selection/highlight to `state.snapshot` so remote clients and future web clients can see which saved history entry the server-side replay browser currently has selected.

## Changes

- Updated `snapshot_from_app()` to populate `replay_browser.selected_history_entry` from the current replay-list highlight when the replay browser is open.
- Covered the serializer path directly and through the headless-server replay flow so replay snapshots now include the selected saved entry after remote replay-browser actions.
- Verified with `uv run python3 -m unittest tests/test_control_room_protocol.py tests/test_control_room_server.py` and `uv run python3 -m unittest discover -s tests`.
- Ran the required timing breakdown after the full suite reported `1.241s`; `tools/report_test_timing.py` showed no single dominant regression, with the slowest test at `0.061s`.

## Follow-ups

- Decide whether replay selection should become broker-owned session state instead of remaining a serialized reflection of the app/headless host state.
- Keep an eye on full-suite timing on the next slices in case the slower wall-clock run reflects environment drift rather than this change.
