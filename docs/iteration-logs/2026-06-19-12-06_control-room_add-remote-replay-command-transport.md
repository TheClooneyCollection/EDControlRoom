# Iteration Log

- Area: `control-room`
- Title: `add-remote-replay-command-transport`
- Started: `2026-06-19 12:06`

## Summary

- Added real remote replay command transport so active operators in `connect` mode can open/filter/close replay history, replay entries, and toggle default haul through the headless server instead of hitting local “not available yet” shims.

## Changes

- Added an `ObserverSessionCommandHandler` shim for server-side session commands and extended WebSocket command handling to support replay-browser open/close, replay filtering, replay execution/edit, and default-haul toggling.
- Taught `HeadlessControlRoomHost` to stub the replay widgets/styles that the existing replay helpers expect, then publish fresh snapshots after replay-state mutations.
- Updated `RemoteObserverBackend` to send real replay command envelopes and added server/client regression coverage for the new command set.
- Verified with `uv run python3 -m unittest tests/test_control_room_server.py tests/test_control_room_client.py` and `uv run python3 -m unittest discover -s tests`.

## Follow-ups

- Live-validate remote replay flows against real history entries, especially `haul` edit/execute and `dest` edit prompts under the headless host.
- Decide whether replay-browser selection/highlight state should remain a client-local concern or be promoted into the server session model for future web clients.
