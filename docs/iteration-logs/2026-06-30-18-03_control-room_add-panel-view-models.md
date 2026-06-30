# Iteration Log

- Area: `control-room`
- Title: `add-panel-view-models`
- Started: `2026-06-30 18:03`

## Summary

- Added the first view-model layer for read-only Control Room panels.

## Changes

- Added status, haul, and market panel view models.
- Added panel-specific rendering entrypoints that accept view models while preserving existing markup helper wrappers.
- Routed status, haul, and market refresh methods through the new panel view models.
- Added focused view-model tests.

## Follow-ups

- Move view-model builders from snapshot-derived app helpers to `ControlRoomDependencies.data_source` once remote data sources replace snapshots.
- Add action objects for interactive views next: command bar, market presentation, replay browser, and trade-route picker.
