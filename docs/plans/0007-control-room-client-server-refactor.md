# 0007: Control Room Client/Server Refactor

## Status

In progress

## Why

Control Room already has the operator UX we want, but it currently mixes runtime ownership, UI rendering, command handling, logging, and TTS in one in-process app.

To support `serve` and `connect` without building a second client UI, we need to separate:

- server-owned runtime state and side effects
- client-rendered view state
- transport-neutral user intents and streamed events

## Goals

- reuse the existing Textual Control Room as both local UI and remote client UI
- make the server authoritative for routines, journal watching, market state, activity logs, and announcement events
- establish typed snapshot and event models before networking work starts

## Current Scope Notes

- TTS playback is intentionally client-local: the server streams announcement events and each client decides whether to speak them.
- LAN shared-token auth is acceptable for the current slice; internet-facing auth is not part of this plan yet.
- One connected client can be the active operator at a time; additional clients are observers.

## Refactor Sequence

### 1. Protocol models

Status: complete

Add `edap/control_room/protocol/` with typed models for:

- `state.snapshot`
- `event.activity_log_appended`
- `event.announcement_emitted`

### 2. Snapshot serialization

Status: complete

Add a serializer that reads current `ControlRoomApp` state and produces a typed snapshot from:

- `ShipState`
- `MarketData`
- `HaulStats`
- `RuntimeUIState`
- `PromptState`
- `ReplayBrowserState`
- `ControlRoomState`

### 3. UI view-state seam

Status: mostly complete

Make the Textual app capable of rendering from a view-state object instead of only from its current internal mutable fields.

- the status, haul, and market panels refresh from backend snapshots
- prompt flows and replay state are backend-owned session state rather than widget-owned state
- the remaining uncertainty is live validation rather than a known missing local view-state seam

### 4. Backend interface

Status: complete for current local/remote needs

Introduce a backend/controller seam so the UI can issue intents through either:

- a local in-process backend
- a remote protocol backend

### 5. Local backend

Status: complete

Wrap the existing in-process behavior behind that backend seam first.

- `LocalControlRoomBackend` now exists and is always attached in embedded/local mode.
- It owns snapshot generation plus local event subscription for activity-log and announcement events.
- The legacy external sink hook remains as a compatibility passthrough for observer transport.

### 6. Event adaptation

Status: complete for activity log, announcement, and snapshot fanout

Adapt existing UI-side effects into transport-neutral events:

- `_log()` to `event.activity_log_appended`
- `_announce_tts()` to `event.announcement_emitted`

### 7. Server mode

Status: complete for LAN observer mode

- `control_room serve` now exposes `GET /health`, `GET /capabilities`, `GET /snapshot`, and `WS /session`
- the server runs through a headless host, in-memory session broker, retained session state, and shared-token auth
- first authenticated client becomes active operator by default; disconnect failover promotes the next client

### 8. Remote backend

Status: complete for current LAN client

- the existing Textual app now runs as a remote client through `control_room connect`
- remote clients consume snapshots, activity-log events, announcement events, and active-operator changes
- remote clients can issue command input, replay actions, prompt Enter/default flows, and remote routine interruption when they hold the active-operator role

## Current Remaining Work

- run deeper live validation against real routine-heavy `serve` / multi-client `connect` sessions
- confirm prompt cancellation, replay flows, reconnect recovery, and failover behavior under live runtime conditions
- decide whether any extra remote operator ergonomics are still needed after that validation

## Acceptance Criteria

- typed snapshot and event models exist under `edap/control_room/protocol/`
- the serializer can map current `ControlRoomApp` state into a typed snapshot without requiring networking code
- local embedded mode still works through the backend seam without changing the day-to-day operator UX
- `serve` and `connect` support one active operator plus observer clients over LAN with retained session state and reconnect recovery
- tests cover key state buckets, server-status derivation, and websocket command/session behavior

## Notes For The Next Agent

- treat the current protocol schema and design note as the wire contract
- do not tunnel existing internal app methods over the network
- keep announcement streaming semantic: clients decide whether to perform local TTS
- use `docs/operators/control-room-remote.md` and `tools/scratch/scratch_control_room_remote.py` as the starting point for live validation
