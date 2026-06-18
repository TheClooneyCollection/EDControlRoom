# 0007: Control Room Client/Server Refactor

## Status

Draft

## Why

Control Room already has the operator UX we want, but it currently mixes runtime ownership, UI rendering, command handling, logging, and TTS in one in-process app.

To support `serve` and `connect` without building a second client UI, we need to separate:

- server-owned runtime state and side effects
- client-rendered view state
- transport-neutral user intents and streamed events

## Goals

- reuse the existing Textual Control Room as both local UI and remote client UI
- make the server authoritative for routines, journal watching, market state, activity logs, and TTS announcement events
- establish typed snapshot and event models before networking work starts

## Non-Goals

- no transport implementation in the first slice
- no full backend abstraction in the first slice
- no command routing over WebSocket yet

## Refactor Sequence

### 1. Protocol models

Add `edap/control_room/protocol/` with typed models for:

- `state.snapshot`
- `event.activity_log_appended`
- `event.announcement_emitted`

### 2. Snapshot serialization

Add a serializer that reads current `ControlRoomApp` state and produces a typed snapshot from:

- `ShipState`
- `MarketData`
- `HaulStats`
- `RuntimeUIState`
- `PromptState`
- `ReplayBrowserState`
- `ControlRoomState`

### 3. UI view-state seam

Make the Textual app capable of rendering from a view-state object instead of only from its current internal mutable fields.

Current status:

- the status, haul, and market panels now refresh from a backend snapshot
- the app still owns the underlying local mutable state in embedded mode
- command input, prompt-confirm flows, destination dispatch, and haul-loop launch now route through backend intent methods
- replay-browser open/filter/execute/edit/default-haul actions now route through backend intent methods too
- remote operator-command transport and command-history/session ownership still need to move fully onto the backend seam

### 4. Backend interface

Introduce a backend/controller seam so the UI can issue intents through either:

- a local in-process backend
- a remote protocol backend

### 5. Local backend

Wrap the existing in-process behavior behind that backend seam first.

Current status:

- `LocalControlRoomBackend` now exists and is always attached in embedded/local mode.
- It owns snapshot generation plus local event subscription for activity-log and announcement events.
- The legacy external sink hook remains as a compatibility passthrough for observer transport while the broader UI refactor is still underway.

### 6. Event adaptation

Adapt existing UI-side effects into transport-neutral events:

- `_log()` to `event.activity_log_appended`
- `_announce_tts()` to `event.announcement_emitted`

### 7. Server mode

Implement `control_room serve` with:

- `GET /health`
- `GET /capabilities`
- `GET /snapshot`
- `WS /session`

Observer mode should land before active-operator command routing.

### 8. Remote backend

Implement a remote backend that consumes snapshots and streamed events and sends user intents.

## Immediate Slice

Build only phases 1 and 2 now:

- scaffold protocol Python types
- implement `snapshot_from_app()`
- add tests proving current app state maps into the typed snapshot shape

Follow-up slice now in progress:

- move event publication onto the always-present local backend
- keep `serve` compatible through an external sink passthrough
- then move rendering and operator intents onto the backend seam panel by panel

## Acceptance Criteria

- typed snapshot and event models exist under `edap/control_room/protocol/`
- the serializer can map current `ControlRoomApp` state into a typed snapshot without requiring networking code
- tests cover the key state buckets and server-status derivation

## Notes For The Next Agent

- treat the current protocol schema and design note as the wire contract
- do not tunnel existing internal app methods over the network
- keep announcement streaming semantic: clients decide whether to perform local TTS
