# Iteration Log

- Area: `control-room`
- Title: `remote-validation-playbook`
- Started: `2026-06-19 17:44`

## Summary

- Added a dedicated remote-operator validation runbook and a lightweight HTTP/websocket scratch probe so the remaining `serve` / `connect` risk can be exercised without relying on memory or the full Textual client.

## Changes

- Added `docs/operators/control-room-remote.md` with LAN startup, active-operator semantics, reconnect/failover checks, prompt-cancel expectations, and a concrete live validation sequence.
- Added `tools/scratch/scratch_control_room_remote.py` plus `tools/scratch/README.md` coverage for transport-only probing of `health`, `capabilities`, `snapshot`, and websocket session events.
- Updated `docs/operators/control-room.md`, `docs/plans/0007-control-room-client-server-refactor.md`, and `docs/status/control-room.md` so the current server/client split, client-local TTS behavior, and remaining validation work are described accurately.

## Follow-ups

- Run the new remote validation playbook against real multi-client LAN sessions and capture any routine-heavy or market-recovery gaps that still appear under live runtime conditions.
