# Iteration Log

- Area: `control-room`
- Title: `priority-interrupt-exit-bindings`
- Started: `2026-07-04 20:38`

## Summary

- Fixed the connect-mode `Ctrl-D` exit regression where a remote-active detach prompt could be opened but repeated `Ctrl-D` did not take the default detach/exit path.

## Changes

- Converted Control Room `Ctrl-C` and `Ctrl-D` bindings to priority `Binding` objects so interrupt and exit handling wins over focused command-input widget bindings in local and `connect` mode.
- Changed remote-active exit handling so the first `Ctrl-D` opens the detach prompt and a following `Ctrl-D` exits the client without cancelling the server routine.
- Routed raw control-character key events for `\x03`/`\x04` through the same interrupt/exit handlers in case a terminal path reports control keys by character instead of normalized Textual key name.
- Kept connect-client shutdown flags local during remote data refreshes so server hydrate state cannot overwrite an in-progress client exit.
- Added regression coverage for priority interrupt/exit bindings and the connect-mode remote detach `Ctrl-D` sequence.
- Updated the Control Room status handoff with the current binding-priority behavior.

## Follow-ups

- Live-check a real `control_room.py connect` terminal during an active remote routine to confirm double `Ctrl-D` exits/detaches as expected with the command bar focused.
