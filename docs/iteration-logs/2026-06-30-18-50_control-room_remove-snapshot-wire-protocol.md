# Iteration Log

- Area: `control-room`
- Title: `remove-snapshot-wire-protocol`
- Started: `2026-06-30 18:50`

## Summary

- Removed the legacy snapshot message family from the remote `serve` / `connect` wire protocol.

## Changes

- Removed `/snapshot` from the observer server routes and stopped handling `command.request_snapshot`.
- Removed `state.snapshot` and `command.request_snapshot` from advertised capabilities and the JSON message schema enum.
- Changed broker snapshot publication to retain server-local state without broadcasting snapshot messages.
- Updated the browser probe to use `/hydrate` and `control_room.hydrate` instead of snapshot fetch/request flows.
- Updated server/client/schema tests and remote operator docs for the hydrate-only remote surface.

## Follow-ups

- Remove remaining internal/local snapshot compatibility after command bar, replay browser, and trade-route picker state are fully data-source/view-action owned.
