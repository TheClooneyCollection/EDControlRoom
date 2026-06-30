# Iteration Log

- Area: `control-room`
- Title: `remove-remote-snapshot-events`
- Started: `2026-06-30 19:12`

## Summary

- Removed remote snapshot update events from the connect client backend.

## Changes

- `RemoteObserverBackend.publish_snapshot()` now only updates its temporary compatibility cache and emits no backend event.
- Removed the unreachable connect app snapshot-event branch and stale imports.
- Updated client tests to assert compatibility-cache updates are silent.

## Follow-ups

- Remove the temporary compatibility cache once `ControlRoomApp` no longer needs a constructor-time `_view_snapshot`.
