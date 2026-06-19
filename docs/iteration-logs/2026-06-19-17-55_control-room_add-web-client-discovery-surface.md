# Iteration Log

- Area: `control-room`
- Title: `add-web-client-discovery-surface`
- Started: `2026-06-19 17:55`

## Summary

- Added browser-friendly HTTP discovery support for the remote observer server so future web clients can fetch capabilities and the wire schema directly instead of relying on same-origin coupling or repo-local files.

## Changes

- Added permissive CORS middleware to the observer server HTTP surface and kept websocket auth/query-token behavior unchanged.
- Added `GET /schema/control_room_message.json` plus a `message_schema_url` field in `/capabilities` so external clients can fetch the current wire contract from the server itself.
- Covered the new discovery surface with server tests and updated the protocol/design/status docs to reflect the browser-client path.

## Follow-ups

- Use the served schema and capability metadata as the starting point if a dedicated browser client is introduced, then decide whether any additional browser-specific session ergonomics are needed after live LAN validation.
