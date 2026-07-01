# 0008: Control Room Composable App Refactor

## Status

Planned

## Why

The current `serve` / `connect` implementation still treats a bundled snapshot as app state. That causes remote data refreshes to collide with local user interaction state such as command edits, prompt prefill, route-picker selection, replay filters, market display lock, and cursor position.

The next architecture should make Control Room local-first at the app boundary. Remote mode should be the same app composed with remote data and execution dependencies, not a subclass or a second UI that receives app snapshots.

## Core Decision

Remove the snapshot model entirely.

The server may send a bundled hydration message containing the latest data from every data source, but that message is not an app snapshot and must not include UI state. There will be no compatibility adapter for the current snapshot protocol.

## Target Shape

There is one `ControlRoomApp`.

Modes differ only by composed dependencies:

- `local`: local data sources plus local execution
- `serve`: local data sources plus local execution plus remote transport
- `connect`: remote data sources plus remote execution

The app is built from these layers:

- `DataSource`: provides external read models such as ship, market, haul session, command history, activity, routine status, and session status
- `ViewModel`: translates data source read models plus local UI state into exactly what each view needs
- `View`: dumb display adapters/widgets that render supplied view models and call view actions; Textual is the current adapter, not the architecture boundary
- `ViewActions`: UI-neutral intent dispatchers for each view; they depend on injected action dependencies and do not know whether the caller is Textual, a browser UI, or an API
- `Execution`: performs real side effects, either local routines/input-driver work or remote execution intents

## Ownership Rules

- UI state is always local to `ControlRoomApp`.
- Remote data hydrates data sources only.
- Remote messages never contain prompt state, command input text, cursor position, focus, route-picker open state, highlighted row, replay browser state, market filter, market tab, or market display lock.
- Views do not know whether data is local or remote.
- ViewModels do not perform side effects.
- ViewActions are thin and testable; they dispatch through injected dependencies, and real side effects live behind execution or view-action dependency adapters.
- ViewActions must not import Textual/Rich widgets, call `query_one()`, manage focus directly, or know about `ControlRoomApp`.
- Textual, browser, REST, and websocket surfaces should reuse the same ViewModels and ViewActions by supplying different view-action dependency implementations.
- Freeform backend commands are allowed only when the command is intentionally server-owned.

## Protocol Direction

Replace `state.snapshot` with source-oriented messages:

- `control_room.hydrate`
- `ship.updated`
- `market.updated`
- `haul.updated`
- `history.updated`
- `activity.appended`
- `session.updated`
- `routine.updated`
- `execution.accepted`
- `execution.failed`

`control_room.hydrate` is a data-source hydration bundle, not serialized app state.

## Refactor Sequence

### 1. Define domain read models and dependency protocols

Add explicit data source and execution protocols around the data the UI actually renders and the actions it can request.

### 2. Introduce local data sources and local execution

Make embedded local mode use the new interfaces first, while preserving current operator behavior.

### 3. Split views from view models

Move panel rendering toward dumb view update methods fed by view models. Start with low-risk panels such as status, haul stats, and market before prompt-heavy surfaces.

### 4. Decouple view actions from display mechanisms

Keep each action layer as UI-neutral intent code. Textual-specific behavior such as widget focus, Rich markup logging, and `query_one()` calls belongs in an adapter injected into the action layer, not in ViewActions themselves.

### 5. Move interaction state into local UI state objects

Command bar, prompts, replay browser, trade-route picker, and market presentation state should be local app/view-action state, not backend or transport state.

### 6. Rebuild serve transport around data and execution

Expose local data-source updates and accept explicit execution intents. Do not expose app state.

### 7. Rebuild connect mode through dependencies

Wire the same `ControlRoomApp` with remote data sources and remote execution. Delete `ObserverControlRoomApp` as a target architecture artifact.

### 8. Delete snapshot-era code

Remove `ControlRoomSnapshot`, snapshot serializers/deserializers, snapshot events, snapshot schema support, and snapshot-driven backend behavior once their replacements land.

## Acceptance Criteria

- There is only one app class for local and connect UI.
- Connect mode uses the same views, view models, and view actions as local mode.
- No remote message can overwrite local command input, prompt state, picker selection, replay state, market presentation state, focus, or cursor position.
- The server protocol contains data-source events and execution responses, not app snapshots.
- Local mode, serve mode, and connect mode differ only by dependency wiring.
- Tests can exercise view models and view actions without Textual, Rich widgets, `ControlRoomApp`, or a websocket server.

## Non-Goals

- No backward compatibility with the current snapshot protocol.
- No temporary snapshot adapter.
- No second remote UI implementation.
- No broad routine rewrite beyond the execution interface needed by this plan.

## First Implementation Slice

Start by introducing the protocol interfaces and local dependency wiring without changing the visible UI. Once local mode is running through the new dependency boundary, replace one view at a time and keep tests focused on ownership rules.
