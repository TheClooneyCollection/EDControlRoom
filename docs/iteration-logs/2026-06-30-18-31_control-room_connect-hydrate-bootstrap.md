# Iteration Log

- Area: `control-room`
- Title: `connect-hydrate-bootstrap`
- Started: `2026-06-30 18:31`

## Summary

- Removed the production connect-mode bootstrap dependency on the legacy `/snapshot` endpoint.

## Changes

- Added a hydrate-data initializer for the legacy view snapshot shape that `ControlRoomApp` still needs during construction.
- Changed `connect_observer_mode()` to fetch `/hydrate` only, then build the initial remote backend state from the hydrated data source.
- Stopped websocket connect/reconnect and replay refresh from issuing `command.request_snapshot`; live updates now rely on server hydrate messages.
- Added client tests for hydrate-derived initial state and reconnect behavior.

## Follow-ups

- Remove the remaining explicit `request_snapshot()` protocol surface after the server/client observer compatibility tests are retired.
