# Iteration Log

- Area: `control-room`
- Title: `stream-websocket-hydrate-data`
- Started: `2026-06-30 18:25`

## Summary

- Added websocket hydrate message handling for remote data sources.

## Changes

- Server websocket sessions now send `control_room.hydrate` after `event.connection_ready` when a data provider is available.
- `RemoteObserverBackend` can consume Control Room data messages, hydrate its `RemoteObserverDataSource`, and emit `DataUpdatedEvent`.
- `ObserverControlRoomApp` refreshes data-source-backed panels from `DataUpdatedEvent`.
- Added client and server tests for websocket/data-message hydration.

## Follow-ups

- Broadcast source-oriented update messages on live data changes instead of relying on snapshot fanout.
- Remove old snapshot bootstrap and snapshot websocket handling from connect mode.
