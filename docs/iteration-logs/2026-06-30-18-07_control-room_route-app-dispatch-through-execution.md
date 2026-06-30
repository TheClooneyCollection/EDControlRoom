# Iteration Log

- Area: `control-room`
- Title: `route-app-dispatch-through-execution`
- Started: `2026-06-30 18:07`

## Summary

- Routed app-level routine/command dispatch helpers through composable execution dependencies.

## Changes

- Added `RemoteObserverExecution` so connect mode has a remote execution dependency backed by the websocket backend.
- Updated `ObserverControlRoomApp` to install the remote execution dependency after construction.
- Switched `_dispatch_command`, `_dispatch_dest`, `_dispatch_haul_loop`, and haul prompt handlers to `ControlRoomDependencies.execution`.
- Added remote execution wrapper tests.

## Follow-ups

- Continue moving remaining app/backend command paths, especially interrupt and replay/picker actions, toward explicit view actions and execution dependencies.
