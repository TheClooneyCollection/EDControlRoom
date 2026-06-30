# Iteration Log

- Area: `control-room`
- Title: `remove-app-snapshot-state`
- Started: `2026-06-30 21:38`

## Summary

- Removed `ControlRoomApp`'s direct dependency on backend snapshots.

## Changes

- Dropped `_view_snapshot`, `_sync_view_snapshot`, `_apply_view_snapshot_state`, and snapshot-backed view helper methods from the shared app.
- Updated app snapshot publication to build from the app directly for the remaining legacy external sink path instead of asking the backend for `current_snapshot()`.
- Reworked local/remote tests to seed app state or hydrate data sources directly rather than applying snapshots to the app.
- Verified focused control-room/client/protocol tests and the full unittest suite.

## Follow-ups

- Continue pruning backend/server snapshot compatibility and then validate live `serve` + `connect`.
