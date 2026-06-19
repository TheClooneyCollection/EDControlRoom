# Iteration Log

- Area: `control-room`
- Title: `add-server-session-state-cache`
- Started: `2026-06-19 11:58`

## Summary

- Added a thin in-memory `ControlRoomServerState` behind the observer broker so remote sessions get server-owned activity history and retained announcement events instead of depending only on app-private caches.

## Changes

- Added `edap/control_room/server/state.py` with capped activity-log and announcement retention plus snapshot merge support.
- Updated `InMemoryObserverSessionBroker` to record activity/announcement events into server state and to reapply retained activity history whenever it serves or rebroadcasts snapshots.
- Added tests covering new-session snapshot history replay and capped announcement retention.
- Verified with `uv run python3 -m unittest tests/test_control_room_server.py`, `uv run python3 -m compileall edap tests`, and `uv run python3 -m unittest discover -s tests`.

## Follow-ups

- Move replay-browser/session-owned state onto the same server-side seam so connect clients stop relying on app-local replay caches.
- Decide whether retained announcement history should be exposed directly to future web clients or only kept for reconnect/session continuity.
