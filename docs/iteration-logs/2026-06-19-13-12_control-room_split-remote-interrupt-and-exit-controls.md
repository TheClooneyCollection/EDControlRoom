# Iteration Log

- Area: `control-room`
- Title: `split-remote-interrupt-and-exit-controls`
- Started: `2026-06-19 13:12`

## Summary

- Split connected-client quit controls so remote `Ctrl-C` requests routine cancellation while `Ctrl-D` becomes a two-step local exit with a remote-routine detach/cancel prompt.

## Changes

- Added backend/server command shims for `command.cancel_active_routine` so remote operators can interrupt server-side work without sending `quit` to the headless host.
- Split `ControlRoomApp` bindings into interrupt vs exit actions, made terminal `SIGINT` follow the interrupt path, and added the local confirmation flow for exiting a connected active-operator client while a remote routine is still running.
- Added regression coverage across app, client, and server tests for remote interrupt transport and the new exit semantics.

## Follow-ups

- Live-validate the new `Ctrl-C`/`Ctrl-D` flow against a real connected client, especially during haul and prompt-heavy routines, before merging another remote-control slice on top.
