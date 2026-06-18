# Iteration Log

- Area: `control-room`
- Title: `client-server-protocol-draft`
- Started: `2026-06-15 14:42`

## Summary

- Drafted the first Control Room client/server protocol around HTTP plus WebSocket for LAN use, with browser-compatible transport, full-word wire property names, and an explicit one-operator-plus-observers session model.

## Changes

- Added `docs/design/0002-control-room-client-server-protocol.md` with transport choice, topology, CLI direction, message vocabulary, payload contracts, and LAN/auth constraints.
- Added `docs/schemas/control_room_message.schema.json` for the versioned JSON envelope and initial command, event, state, and response payload families, including `client_role`, active-operator change events, announcement streaming, and a concrete `state.snapshot` shape mapped to current Control Room models.
- Added `docs/plans/0007-control-room-client-server-refactor.md` plus the first `edap/control_room/protocol/` Python types and `snapshot_from_app()` serializer with focused tests.
- Wired `ControlRoomApp._log()` and `ControlRoomApp._announce_tts()` into protocol-native activity-log and announcement caches so the future server path can stream existing operator outputs without changing UI behavior.
- Added a thin `ControlRoomEventSink` shim, an in-memory observer session broker, a headless runtime host, a Starlette observer server surface, and `control_room serve` wired to observer mode with tested HTTP/WebSocket endpoints.
- Updated control-room handoff status so the next session can resume from the protocol direction instead of rediscovering it.

## Follow-ups

- Extend the first serializer so replay selection and announcement history come from a real server-side state cache instead of direct app-owned lists.
- Add authentication and a concrete `connect` client path on top of the observer server surface.
- Decide whether the active operator may be explicitly transferred or only replaced by disconnect/reconnect in the first implementation.
