# Iteration Log

- Area: `control-room`
- Title: `add-composable-dependency-layer`
- Started: `2026-06-30 17:58`

## Summary

- Introduced the first bottom-up implementation slice for plan 0008: a composable data-source and execution dependency layer for Control Room.

## Changes

- Added `edap.control_room.dependencies` with read models, data-source and execution protocols, local data-source copying, local execution delegation, and a dependency bundle.
- Attached a `ControlRoomDependencies` bundle to `ControlRoomApp`, defaulting to local data and execution dependencies while preserving current backend behavior.
- Added focused tests for local data-source read models and local execution delegation.

## Follow-ups

- Move local rendering surfaces to view models fed by `ControlRoomDependencies.data_source`.
- Replace backend command paths with `ControlRoomDependencies.execution` after local behavior is covered by tests.
