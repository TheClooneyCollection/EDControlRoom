# Iteration Log

- Area: `control-room`
- Title: `state-drive-replay-selection`
- Started: `2026-06-19 17:08`

## Summary

- Removed the replay-selection widget side-channel by making the selected replay history entry explicit application state, which the local widget now mirrors and remote snapshots now serialize directly.

## Changes

- Added retained replay selection state to `ReplayBrowserState` and exposed it on `ControlRoomApp`, so replay selection no longer depends on reading `OptionList.highlighted` as the source of truth.
- Updated replay-browser helpers to preserve and resolve the selected history entry across open, refresh, filter, and close flows, while synchronizing the widget highlight from state and synchronizing state from highlight events.
- Changed protocol snapshot generation to read the selected replay history entry from replay state instead of querying the UI widget directly.
- Updated remote snapshot application to restore replay selection into app state and re-highlight the local replay widget when a server snapshot carries a selected replay entry.
- Verified with targeted protocol/server tests and `uv run python3 -m unittest discover -s tests` (`479 tests in 0.216s`).

## Follow-ups

- Move prompt mutation itself onto explicit server-owned state transitions so the headless server path no longer depends on app-local prompt orchestration.
- Decide whether replay-browser navigation should grow an explicit server-native selection command model or remain a thin mirror of local widget navigation for now.
