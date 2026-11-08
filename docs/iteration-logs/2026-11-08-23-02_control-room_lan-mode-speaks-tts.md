# Iteration Log

- Area: `control-room`
- Title: `lan-mode-speaks-tts`
- Started: `2026-11-08 23:02`

## Summary

- `serve`/`lan`/`local` now speak TTS on the server host by default, so the Steam Deck no longer needs a `connect` TUI just for callouts.

## Changes

- `HeadlessControlRoomHost` takes a required `speech_backend`; `serve_observer_mode` takes a required `speak_tts` and builds the platform or Piper backend (`tts.piper`) when it is set.
- New `--no-tts` flag keeps the server silent. A `connect` TUI also speaks every server announcement (`_play_local_announcement`), so a TUI on the same machine as `lan` needs `lan --no-tts` to avoid double callouts.
- With a real backend the announcer now dedups consecutive identical callouts on the server too, so a repeated identical line is no longer re-broadcast to clients (same as the embedded TUI).
- README and getting-started describe the new default.

## Follow-ups

- Mac Piper support is paused: the official macOS binary misses `libespeak-ng`, and PyPI `piper-tts` 1.8 (installed on the Mac via `uv tool`) logs `Wrote <path>` to stderr instead of printing the path to stdout, so `PiperSpeechBackend` needs to read either.
