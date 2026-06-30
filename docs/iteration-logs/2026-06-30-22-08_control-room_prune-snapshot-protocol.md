# Iteration Log

- Area: `control-room`
- Title: `prune-snapshot-protocol`
- Started: `2026-06-30 22:08`

## Summary

- Deleted legacy Control Room snapshot protocol modules and schema definitions after replacing server/client refresh with data-source hydration.

## Changes

- Moved `ActivityLogEntry` into protocol events so event streaming no longer depends on `protocol.snapshot`.
- Deleted `edap/control_room/protocol/snapshot.py` and `protocol/from_app.py`.
- Removed snapshot exports from `edap.control_room.protocol`.
- Removed snapshot `$defs` from `docs/schemas/control_room_message.schema.json`.
- Renamed internal status/market sync helpers away from snapshot-era terminology.

## Follow-ups

- Continue extracting explicit ViewModel/action seams for panels that still read app state directly.
