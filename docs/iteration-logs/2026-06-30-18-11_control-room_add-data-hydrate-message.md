# Iteration Log

- Area: `control-room`
- Title: `add-data-hydrate-message`
- Started: `2026-06-30 18:11`

## Summary

- Added the first no-snapshot, source-oriented data protocol message for plan 0008.

## Changes

- Added `edap.control_room.protocol.data_messages` with a distinct data-message schema, supported source-oriented message types, and `control_room.hydrate` construction from `ControlRoomDataReadModel`.
- Exported the data-message primitives from `edap.control_room.protocol`.
- Added tests proving hydrate payloads contain data-source read models and omit UI-owned prompt/replay state.

## Follow-ups

- Wire `serve` to emit `control_room.hydrate` from `ControlRoomDependencies.data_source`.
- Build remote data sources that consume hydrate/update messages directly instead of snapshots.
