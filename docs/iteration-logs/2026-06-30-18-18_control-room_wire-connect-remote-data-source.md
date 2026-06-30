# Iteration Log

- Area: `control-room`
- Title: `wire-connect-remote-data-source`
- Started: `2026-06-30 18:18`

## Summary

- Wired connect-mode app construction to install the new remote hydrate data source.

## Changes

- Updated `connect_observer_mode()` to fetch `/hydrate` and build `RemoteObserverDataSource`.
- Updated `ObserverControlRoomApp` to accept a remote data source and install it into `ControlRoomDependencies`.
- Added a client test proving connect-mode app dependencies use the supplied remote data source.

## Follow-ups

- Replace the remaining snapshot bootstrap and websocket stream in connect mode with hydrate/update data messages.
