# Iteration Log

- Area: `control-room`
- Title: `remove-server-snapshot-refresh`
- Started: `2026-06-30 21:54`

## Summary

- Removed the server-side snapshot refresh path so `serve` reads metadata and hydrates clients from the composed data source.

## Changes

- Replaced `ControlRoomEventSink.publish_snapshot()` with `publish_data_refresh()`.
- Removed broker snapshot retention/merge logic and server-state command-history snapshot merging.
- Removed `HeadlessControlRoomHost.snapshot()` and serve-time snapshot seeding.
- Updated websocket/HTTP tests to construct the server around `_base_data_read_model`.

## Follow-ups

- Prune remaining legacy protocol snapshot dataclasses/conversion helpers once local tests no longer need them as fixtures.
