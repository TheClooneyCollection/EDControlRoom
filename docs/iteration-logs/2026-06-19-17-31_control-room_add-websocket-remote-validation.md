# Iteration Log

- Area: `control-room`
- Title: `add-websocket-remote-validation`
- Started: `2026-06-19 17:31`

## Summary

- Added websocket-level integration coverage for the observer server path so active-operator failover and replay-navigation commands are now exercised through the actual session protocol, not only through unit-level helpers.

## Changes

- Added `TestClient` websocket coverage proving that when the active operator disconnects, the remaining connected client receives the promotion event and subsequent personalized snapshot as the new `active_operator`.
- Added websocket-session coverage proving `command.move_replay_selection` is accepted over the observer protocol and reaches the server command handler.
- Re-ran the full test suite with `uv run python3 -m unittest discover -s tests` (`491 tests in 0.225s`).

## Follow-ups

- Live-validate routine-heavy remote execution, prompt-heavy flows, and failure/recovery wording under real `serve` / `connect` sessions.
- Decide whether any further remote operator ergonomics are needed once live validation is done.
