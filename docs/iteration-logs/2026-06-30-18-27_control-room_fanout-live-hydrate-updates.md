# Iteration Log

- Area: `control-room`
- Title: `fanout-live-hydrate-updates`
- Started: `2026-06-30 18:27`

## Summary

- Added live hydrate fanout from the headless server to connected websocket clients.

## Changes

- Added broker support for queueing already-formed data messages.
- Added `DataHydrateFanoutSink`, which broadcasts `control_room.hydrate` from the server data source whenever the headless host publishes runtime changes.
- Wired `control_room serve` to include the hydrate fanout sink.
- Updated websocket sending so data messages keep their no-snapshot schema instead of being wrapped in the old command/event schema.
- Added server tests for hydrate fanout.

## Follow-ups

- Remove snapshot fanout once connect no longer depends on snapshot-driven UI state.
