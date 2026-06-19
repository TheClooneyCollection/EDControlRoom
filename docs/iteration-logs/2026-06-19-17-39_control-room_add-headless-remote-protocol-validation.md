# Iteration Log

- Area: `control-room`
- Title: `add-headless-remote-protocol-validation`
- Started: `2026-06-19 17:39`

## Summary

- Added websocket-session coverage that drives the actual headless observer host, so prompt-heavy remote protocol flow is now validated locally through the real server path instead of only through helper-level tests.

## Changes

- Added websocket-session integration coverage proving `command.submit_input` can open and resolve a destination prompt against a live `HeadlessControlRoomHost` behind `build_observer_server_app`, with broker-retained snapshot state reflecting the prompt lifecycle.
- Added websocket-session coverage proving `command.request_active_operator` updates broker role assignment over the real observer protocol path.
- Re-ran the full test suite with `uv run python3 -m unittest discover -s tests` (`493 tests in 0.228s`).

## Follow-ups

- Live-validate routine-heavy remote execution, prompt-heavy flows, and failure/recovery wording under real `serve` / `connect` sessions with the actual game/runtime in the loop.
- Decide whether any further remote operator ergonomics are needed once live validation is done.
