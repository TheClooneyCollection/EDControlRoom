# Iteration Log

- Area: `control-room`
- Title: `startup-tts-commander-name`
- Started: `2026-06-27 13:35`

## Summary

- Fixed the control-room startup greeting order so `{title}` resolves against the bootstrapped commander name before the first TTS line is rendered.

## Changes

- Moved local `ControlRoomApp` startup greeting emission to run after `_bootstrap_ship_state()`.
- Moved headless observer-server host startup greeting emission to run after `_bootstrap_ship_state()` so remote announcement streams stay consistent with local startup behavior.
- Added regression coverage for both local app mount and headless host start paths when `tts.title_mode = "commander_name"`.
- Ran `uv run python3 -m unittest discover -s tests` and the required timing report because the suite currently exceeds the `0.3s` target.

## Follow-ups

- Full-suite runtime remains above target (`0.550s` / `0.581s` in the timing report); the slowest tests are still remote control-room client flows rather than this startup-TTS change.
