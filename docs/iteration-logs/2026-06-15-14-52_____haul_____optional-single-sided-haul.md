# Iteration Log

- Area: `haul`
- Title: `optional-single-sided-haul`
- Started: `2026-06-15 14:52`

## Summary

- Made two-station `haul` accept a blank station-1 or station-2 buy commodity as long as the opposite station still defines a valid outbound cargo leg.

## Changes

- Relaxed Control Room haul prompt and launch validation so both station buy prompts are optional, while launch still rejects the command when both buy commodities are blank.
- Updated two-way haul help text and launch labels to show missing buy legs explicitly instead of rendering an empty commodity name.
- Taught `edap.routines.haul_two_way` to skip missing buy/sell phases cleanly and to resume out of docked states by undocking immediately when the current station has no configured buy cargo.
- Added coverage for one-sided haul dispatch and one-sided haul iteration / phase-detection behavior.

## Follow-ups

- Live-test a station-1-only and station-2-only haul loop in-game to confirm menu timing, cargo detection, and resume semantics match the simulated path.
