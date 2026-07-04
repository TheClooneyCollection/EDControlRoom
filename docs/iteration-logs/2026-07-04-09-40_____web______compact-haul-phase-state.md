# Iteration Log

- Area: `web`
- Title: `compact-haul-phase-state`
- Started: `2026-07-04 09:40`

## Summary

- Replaced the web haul phase guess with compact state projected from the existing two-way haul `Phase` enum.

## Changes

- Added an optional `phase_updated_fn` callback to `haul_loop_two_way()` and wired Control Room dispatch to publish `sell|buy|undock|depart|transit` plus station index.
- Stored compact haul phase state in `RuntimeUIState`, hydrate read models, and hydrate parsing so local and remote clients preserve the same routine state.
- Updated `/haul` to render five reusable phase steps with a station 1/2 indicator instead of six guessed route steps.
- Added focused tests for phase callback propagation, hydrate parsing, and the web phase projection mapping.

## Follow-ups

- Live-check the phase strip during a real two-way run to confirm operator-visible timing around skipped sell/buy legs.
