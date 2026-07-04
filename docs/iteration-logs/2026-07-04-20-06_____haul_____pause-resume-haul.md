# Iteration Log

- Area: `haul`
- Title: `pause-resume-haul`
- Started: `2026-07-04 20:06`

## Summary

- Added operator pause/resume for the two-way haul loop so web and TUI users can request a station-boundary pause at either haul station, freeze haul stats while paused, and resume the same running routine.

## Changes

- Added `pause` / `resume` Control Room commands; `pause` requests the next station-side boundary and `resume` either cancels a pending pause or releases an active pause.
- Extended two-way haul with pause hooks before station 1 or station 2 buy/departure, and wired Control Room pause state through hydrate read models for TUI/connect/web visibility.
- Added haul stats pause/resume helpers that freeze session and current-run elapsed timers while the routine is paused at station.
- Added `/haul` Pause and Resume buttons that submit the same command path as TUI commands and render `Pause requested` / `Paused` routine status.
- Added regression coverage for web controls, TUI command behavior, stats timer freeze/resume, dispatch callback plumbing, and station 2 pause handling.

## Follow-ups

- Live-check a pause request during transit and at both stations to confirm the operator-facing timing and log wording feel right in-game.
