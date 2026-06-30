# Iteration Log

- Area: `control-room`
- Title: `render-panels-from-data-source`
- Started: `2026-06-30 18:21`

## Summary

- Moved the first rendered panels from snapshot-derived app helpers to the composable data-source dependency.

## Changes

- Updated status and haul panel view-model builders to read from `ControlRoomDependencies.data_source`.
- Updated market presentation sync to read latest market data from the data source while keeping display lock state local.
- Updated tests to assert panel rendering and connect market lock behavior through data-source hydration rather than backend snapshots.

## Follow-ups

- Remove remaining `_sync_view_snapshot()` calls from read-only panel refresh paths.
- Add websocket data update streaming so remote data sources hydrate continuously without snapshots.
