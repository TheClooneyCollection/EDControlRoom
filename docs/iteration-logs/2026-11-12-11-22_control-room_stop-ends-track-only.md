# Iteration Log

- Area: `control-room`
- Title: `stop-ends-track-only`
- Started: `2026-11-12 11:22`

## Summary

- First live Track only run, side by side with an assisted haul: Track only could not be stopped from `/haul` or `/controls`. Stop now / Stop after run were disabled because no routine runs, and only the small Stop stats button in the stats panel sent `stop`.

## Changes

- `_cancel_active_routine` ends tracking first (`_stop_haul_tracking`) when no routine runs, for `now`, `after_run` and Ctrl-C toggle; `POST /api/stop` accepts while tracking.
- `/haul` and `/controls` enable their stop buttons while `haul_session.tracking` is active; `/controls` shows `Tracking haul` instead of `Idle`.
- Side-by-side setup: a second `serve` process with its own config (role `standalone`, EDDN off, separate state, runs, recent markets and market DB files, `--port 8766 --no-tts`), since one Control Room has one `HaulStats` and Track only refuses while a routine runs.

## Follow-ups

- Compare the tracked rows against the assisted rows from the same session to check `_track_phase` and run boundaries.
- Track only still needs the route pasted in; inferring station 1/2 from the first buy and sell is a possible follow-up.
