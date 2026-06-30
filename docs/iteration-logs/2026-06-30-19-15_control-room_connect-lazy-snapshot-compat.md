# Iteration Log

- Area: `control-room`
- Title: `connect-lazy-snapshot-compat`
- Started: `2026-06-30 19:15`

## Summary

- Removed production connect's upfront legacy snapshot construction.

## Changes

- `RemoteObserverBackend` now accepts an optional `initial_snapshot`; if absent, `current_snapshot()` lazily derives the temporary compatibility shape from the remote data source.
- `connect_observer_mode()` now passes only `RemoteObserverDataSource` into the backend.
- Added coverage for deriving the compatibility snapshot from hydrated data.

## Follow-ups

- Remove the lazy compatibility snapshot once `ControlRoomApp` construction no longer asks backends for `_view_snapshot`.
