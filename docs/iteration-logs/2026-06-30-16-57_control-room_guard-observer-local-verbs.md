# Iteration Log

- Area: `control-room`
- Title: `guard-observer-local-verbs`
- Started: `2026-06-30 16:57`

## Summary

- Added a transport-level observer guard so client-local verbs like `dest` and `haul` cannot be serialized into `command.submit_input` and sent to the headless server.

## Changes

- Added `_is_client_local_command()` in the remote observer backend and short-circuited both `submit_input()` and `dispatch_command()` for client-local verbs.
- Added a regression proving `dest sol`, `home`, and `market lock` do not enqueue any websocket command payloads from `RemoteObserverBackend`.
- Reverted the partial observer-log filtering experiment so the fix stays at the transport seam rather than hiding server noise in the UI.

## Follow-ups

- Re-run a live `serve` + `connect` `dest sol` session and confirm the server activity stream no longer receives fresh `Command: dest sol` / `Unknown command: dest sol` entries from the observer client.
