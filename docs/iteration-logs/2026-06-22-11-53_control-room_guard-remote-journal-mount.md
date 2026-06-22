# Iteration Log

- Area: `control-room`
- Title: `guard-remote-journal-mount`
- Started: `2026-06-22 11:53`

## Summary

- Guarded `ControlRoomApp.on_mount()` behind the backend mode so remote-backed mounts cannot trip the local journal-directory runtime check.

## Changes

- Added a backend-aware early return in [edap/control_room/app.py](/Users/nicholasclooney/Source/Projects/EDControlRoom/edap/control_room/app.py:679) before local runtime setup.
- Added a regression test in [tests/test_control_room_client.py](/Users/nicholasclooney/Source/Projects/EDControlRoom/tests/test_control_room_client.py:246) that mounts the observer app without a local journal directory.
- Verified `tests/test_control_room_client.py` passes; full `unittest discover -s tests` stays at `0.256s` but currently has one unrelated existing failure in `test_haul_search_uses_current_system_and_updates_trade_routes`.

## Follow-ups

- Re-run a live `control_room connect` session against `serve` to confirm the shipped remote client no longer surfaces the local journal runtime error.
