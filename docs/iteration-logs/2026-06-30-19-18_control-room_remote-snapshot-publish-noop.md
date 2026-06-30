# Iteration Log

- Area: `control-room`
- Title: `remote-snapshot-publish-noop`
- Started: `2026-06-30 19:18`

## Summary

- Made remote backend snapshot publication a no-op.

## Changes

- `RemoteObserverBackend.publish_snapshot()` no longer mutates the compatibility cache.
- Removed redundant snapshot publication calls from connect client tests.
- Updated coverage to assert remote snapshot publication does not change current compatibility state.

## Follow-ups

- Remove the `publish_snapshot()` method from the remote backend surface when `ControlRoomBackend` no longer inherits the snapshot sink protocol.
