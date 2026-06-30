# Iteration Log

- Area: `control-room`
- Title: `prune-backend-replay-actions`
- Started: `2026-06-30 21:15`

## Summary

- Removed the obsolete backend replay-browser action surface after collapsing connect onto the shared app.

## Changes

- Dropped replay browser methods from `ControlRoomBackend`, `LocalControlRoomBackend`, and `RemoteObserverBackend`.
- Routed the remaining app `_replay_history_entry` helper directly through local replay logic.
- Pruned obsolete replay-backend test stubs and the remote backend replay-locality test.
- Verified focused control-room suites and the full unittest suite.

## Follow-ups

- Continue removing internal snapshot compatibility from base app/backend and server broker paths.
