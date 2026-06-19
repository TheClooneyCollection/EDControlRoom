# Iteration Log

- Area: `control-room`
- Title: `retain-remote-session-state`
- Started: `2026-06-19 17:02`

## Summary

- Moved the next real `serve`/`connect` seam into retained server-owned state by having the observer server keep prompt, replay-browser, and command-history session snapshots alongside retained activity history.

## Changes

- Extended `ControlRoomServerState` to retain `command_history`, `prompt_state`, and `replay_browser` snapshots, and to keep `ui_state.replay_browser_open` aligned with retained replay-browser state.
- Updated the observer broker to capture those session slices whenever the headless host publishes a snapshot, so future HTTP/WebSocket snapshot requests are served from server-retained state instead of only whatever the app object currently exposes.
- Threaded a shared `ControlRoomServerState` through `serve_observer_mode` into both the broker and `HeadlessControlRoomHost`, and made the headless host feed retained session state even before an external sink is attached.
- Added regression coverage proving retained prompt/replay state is replayed into later merged snapshots and that the headless host actually populates that retained server state.
- Verified the full suite with `uv run python3 -m unittest discover -s tests` (`478 tests in 0.203s`).

## Follow-ups

- Move the remaining widget-local cursor/highlight semantics and prompt mutation paths behind explicit server-owned state transitions so the remote path no longer depends on app-local UI fields for selection behavior.
- Live-validate prompt-heavy remote flows and replay selection/edit flows against real server/client sessions now that the retained snapshot seam is in place.
