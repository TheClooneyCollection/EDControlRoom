# Iteration Log

- Area: `control-room`
- Title: `connect-single-app-collapse`
- Started: `2026-06-30 19:49`

## Summary

- Collapsed connect mode onto the single local-first `ControlRoomApp` instead of maintaining `ObserverControlRoomApp`.

## Changes

- Replaced the large connect subclass with a small bootstrap that fetches remote hydrate data, builds `RemoteObserverDataSource` / `RemoteObserverExecution`, binds them into `ControlRoomApp`, and runs the shared app.
- Moved remote hydrate/event application into the base app so data-backed panels refresh from the injected data source while command input, prompts, replay, and trade-route picker remain app-local.
- Updated remote execution so prompt-owning/local UI commands execute locally through the shared app, while finalized routine dispatches still go to the server.
- Removed obsolete subclass/snapshot compatibility tests and rewrote protocol assertions around local UI actions plus execution dependency dispatch.
- Verified `tests/test_control_room_client.py`, `tests/test_control_room_protocol.py`, and the full unittest suite.

## Follow-ups

- Continue removing internal snapshot compatibility that remains in the base app/backend after the connect subclass removal.
