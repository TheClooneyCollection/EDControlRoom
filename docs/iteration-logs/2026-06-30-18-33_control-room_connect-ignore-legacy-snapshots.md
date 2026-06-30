# Iteration Log

- Area: `control-room`
- Title: `connect-ignore-legacy-snapshots`
- Started: `2026-06-30 18:33`

## Summary

- Stopped connect-mode UI state from being driven by legacy `state.snapshot` websocket messages.

## Changes

- Remote websocket receive now ignores `SnapshotUpdatedEvent` payloads instead of publishing them into the app.
- Connection loss logs activity only; it no longer rewrites active operator, connected clients, or routine UI state from the transport layer.
- `ObserverControlRoomApp` ignores any remaining manually emitted snapshot backend events.
- Added regression coverage for ignored legacy snapshot events and connection-loss state preservation.

## Follow-ups

- Remove the old snapshot endpoint/message protocol once server compatibility tests are retired.
