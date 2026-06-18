# Iteration Log

- Area: `control-room`
- Title: `remote-observer-tui-backend`
- Started: `2026-06-18 12:43`

## Summary

- Added live observer snapshot broadcasting and replaced the thin `connect` observer CLI with an app-backed remote observer client that reuses the existing Textual Control Room surface in read-only mode.

## Changes

- Extended `ControlRoomEventSink` with snapshot publication and taught the in-memory observer broker to retain the latest base snapshot, merge connected-client state into it, and fan out `state.snapshot` messages to all observer sessions.
- Seeded the broker with the startup snapshot in `serve`, rebroadcasted snapshots on observer connect/disconnect, and published fresh snapshots from the control-room event path after journal-driven state changes, including moving dock-market reload ahead of snapshot emission so observers see updated market data.
- Added a wire-message parser, a `RemoteObserverBackend`, and an observer-mode `ControlRoomApp` mount path so `connect` now renders the existing status/haul/market/activity surfaces from streamed snapshots and announcement events instead of printing lines to stdout.
- Added regression coverage for broker snapshot fan-out, wire parsing, remote-backend read-only behavior, and app-to-sink snapshot publication, then re-ran compile checks and the full unittest suite.

## Follow-ups

- Remote operator commands, remote replay actions, and broader session ownership still need to move onto the backend seam before the same Textual client can take the active-operator role instead of observer-only mode.
