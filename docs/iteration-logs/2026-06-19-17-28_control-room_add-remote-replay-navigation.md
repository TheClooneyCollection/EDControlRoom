# Iteration Log

- Area: `control-room`
- Title: `add-remote-replay-navigation`
- Started: `2026-06-19 17:28`

## Summary

- Added explicit replay-selection navigation commands to the remote protocol so replay movement no longer depends on widget-local behavior as the transport model.

## Changes

- Added backend/server command support for replay selection movement by relative offset, including `command.move_replay_selection` on the observer websocket path.
- Updated the local TUI so replay-browser up/down navigation routes through the backend intent surface instead of bypassing it via `OptionList` behavior.
- Added server/client/protocol coverage proving replay selection movement is serialized over the remote command path and reflected back into snapshots.
- Verified with `uv run python3 -m unittest discover -s tests` (`489 tests in 0.213s`).

## Follow-ups

- Live-validate replay-heavy remote operator sessions, active-operator failover, and routine-heavy command execution under real `serve` / `connect` runs.
- Decide whether any additional remote operator ergonomics are needed after live validation now that replay navigation has an explicit protocol path.
