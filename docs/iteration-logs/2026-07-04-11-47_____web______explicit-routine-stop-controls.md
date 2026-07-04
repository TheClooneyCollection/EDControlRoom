# Iteration Log

- Area: `web`
- Title: `explicit-routine-stop-controls`
- Started: `2026-07-04 11:47`

## Summary

- Replaced the passive Haul Web emergency-stop chip with explicit `Stop after run` and `Stop now` controls backed by websocket stop modes.

## Changes

- Extended `command.cancel_active_routine` with optional `mode` values: legacy `toggle`, deferred haul `after_run`, and immediate `now`.
- Routed explicit stop modes through remote backend, server command handler, headless host, and local execution dependencies into `ControlRoomApp`.
- Added app/server/client/static-web regression coverage for the new stop-mode payloads and controls.

## Follow-ups

- Live-check `Stop after run` and `Stop now` from `/haul` against an active `control_room.py serve` session to confirm operator feedback and TTS feel right in-game.
