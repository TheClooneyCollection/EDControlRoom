# Iteration Log

- Area: `control-room`
- Title: `observer-connect-no-local-journal`
- Started: `2026-06-22 11:24`

## Summary

- Fixed `control_room connect` so remote observer clients can start on machines without a local Elite Dangerous install or resolved journal path.

## Changes

- Let `ControlRoomApp` initialize with no local journal/market path for observer-mode clients while keeping local runtime startup guarded behind an explicit journal requirement.
- Added a regression test that instantiates `ObserverControlRoomApp` with no local journal path and confirmed the full unittest suite still passes in `0.282s`.

## Follow-ups

- Re-run the live multi-machine observer flow to confirm the remote TUI now reaches the initial snapshot cleanly on a non-ED client host.
