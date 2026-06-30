# Iteration Log

- Area: `control-room`
- Title: `connect-apply-data-state`
- Started: `2026-06-30 19:07`

## Summary

- Changed production connect mode to apply hydrated data directly for runtime/history/activity state instead of syncing a backend snapshot.

## Changes

- Added a remote data-state apply path that copies routine state, command history/defaults, activity log, ship context, and commander TTS from `ControlRoomDataReadModel`.
- Kept the legacy snapshot apply path only as a fallback for tests/internal compatibility when no remote data source is supplied.
- Extracted connect-local prompt/replay/trade-route overlay application so both data and fallback paths preserve local UI ownership.
- Added regression coverage proving hydrate data updates local state without refreshing `_view_snapshot`.

## Follow-ups

- Remove the temporary legacy initial view snapshot once `ControlRoomApp` construction no longer requires a backend snapshot.
