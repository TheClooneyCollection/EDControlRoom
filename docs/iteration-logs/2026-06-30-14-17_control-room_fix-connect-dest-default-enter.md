# Iteration Log

- Area: `control-room`
- Title: `fix-connect-dest-default-enter`
- Started: `2026-06-30 14:17`

## Summary

- Fixed the `connect`-mode `dest` default-Enter path so accepting the default settle seconds no longer sends a blank command to the server and crashes with `list index out of range`.

## Changes

- Handled Enter on observer-local prompt steps directly inside `ObserverControlRoomApp.on_key()` instead of falling through to the base prompt handler that calls `backend.submit_input(raw)`.
- Hardened generic command dispatch so blank commands are ignored instead of indexing into an empty token list.
- Added regression coverage for pressing Enter on a remote `dest` prompt with an empty field, asserting that the observer dispatches `command.dispatch_destination` with the configured default settle time.

## Follow-ups

- Re-run the manual `serve` + `connect` `dest sol` flow to confirm the default-Enter path now dispatches the destination routine instead of logging a blank command.
