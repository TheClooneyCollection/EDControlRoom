# Iteration Log

- Area: `control-room`
- Title: `client-server-protocol-draft`
- Started: `2026-06-15 14:42`

## Summary

- Drafted the first Control Room client/server protocol around HTTP plus WebSocket for LAN use, with browser-compatible transport, full-word wire property names, and an explicit one-operator-plus-observers session model.

## Changes

- Added `docs/design/0002-control-room-client-server-protocol.md` with transport choice, topology, CLI direction, message vocabulary, payload contracts, and LAN/auth constraints.
- Added `docs/schemas/control_room_message.schema.json` for the versioned JSON envelope and initial command, event, state, and response payload families, including `client_role` and active-operator change events.
- Updated control-room handoff status so the next session can resume from the protocol direction instead of rediscovering it.

## Follow-ups

- Split the draft schema into implementation-facing Python types once `serve` and `connect` work begins.
- Define the concrete `state.snapshot` shape from current `ControlRoomApp` state instead of the current intentionally broad placeholder objects.
- Decide whether the active operator may be explicitly transferred or only replaced by disconnect/reconnect in the first implementation.
