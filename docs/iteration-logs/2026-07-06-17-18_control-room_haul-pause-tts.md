# Iteration Log

- Area: `control-room`
- Title: `haul-pause-tts`
- Started: `2026-07-06 17:18`

## Summary

- Added explicit TTS announcements for two-way haul pause request acceptance and the station-boundary paused state.

## Changes

- Added `haul_pause_requested` and `haul_paused` announcement IDs plus default TTS phrases.
- Emitted `haul_pause_requested` when the Control Room pause command queues a station pause, and `haul_paused` when the haul loop actually reaches the buy-side station pause gate.
- Added regression coverage for both spoken pause events and default phrase loading.
- Verified the browser `/haul` pause/resume controls already submit the existing server-owned command path, so no client command-surface change was needed.

## Follow-ups

- Full suite passed, but remained above the repo timing budget: `692 tests in 2.259s`; timing reporter also passed and showed unrelated Control Room client/CLI tests as the slowest cases.
