# Iteration Log

- Area: `control-room`
- Title: `haul-cancel-tts`
- Started: `2026-06-19 21:31`

## Summary

- Added explicit spoken feedback for immediate haul cancellation so aborting mid-cycle still produces a clear TTS line without misusing the normal route/session completion announcements.

## Changes

- Added `haul_cancelled` to the TTS announcement IDs and default phrase set.
- Emit the cancellation announcement when haul or multi-leg haul is cancelled immediately instead of only logging the cancel.
- Added regression coverage around the second-interrupt immediate-haul-cancel path.

## Follow-ups

- Live-test remote client double-`Ctrl-C` on haul to confirm the cancellation announcement reaches the observer client as expected.
