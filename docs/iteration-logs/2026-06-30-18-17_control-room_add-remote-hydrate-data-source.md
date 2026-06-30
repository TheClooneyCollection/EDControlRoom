# Iteration Log

- Area: `control-room`
- Title: `add-remote-hydrate-data-source`
- Started: `2026-06-30 18:17`

## Summary

- Added the first remote data-source building block for the no-snapshot `connect` path.

## Changes

- Added hydrate payload parsing into `ControlRoomDataReadModel`.
- Added `RemoteObserverDataSource` as a typed remote read-model cache.
- Added `fetch_remote_control_room_data()` to fetch `/capabilities` plus `/hydrate`.
- Added tests for hydrate round-trip parsing and remote data-source hydration.

## Follow-ups

- Wire `connect` dependencies to `RemoteObserverDataSource`.
- Add websocket data update handling after the server streams source-oriented update messages.
