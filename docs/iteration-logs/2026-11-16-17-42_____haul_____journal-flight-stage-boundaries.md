# Iteration Log

- Area: `haul`
- Title: `journal-flight-stage-boundaries`
- Started: `2026-11-16 17:42`

## Summary

- Fixed Depart showing Complete without timings: normal assisted undocking skipped the routine Depart phase. User approved shared journal flight boundaries.

## Changes

- Undocked starts Depart, the first StartJump starts Transit, and Docked at a route station ends Transit. Later jumps retain the same Transit timer. Routine callbacks cannot advance Depart early or regress a docked leg into Transit.
- Track-only phases use the same source/destination station convention as assisted hauls; its phase and timing data now reach hydrate. Its Undock duration remains unavailable because the journal does not expose the launch request. Station trading phases retain their existing mode-specific triggers.
- Versioned the timing route identity so old boundary samples are not mixed with new measurements; route/run/profit history is preserved.
- Added a simulated-clock flow covering both modes, both directions, multiple hops, delayed routine callbacks, and protocol roundtrip values; updated the recorded journal replay expectations.
- Full suite: 1287 tests in 1.034 s, OK (1 skipped). The localhost HTTP test requires sandbox escalation. Required timing report run because the 0.7722 s budget is exceeded; existing web and transit tests dominate. No unrelated test optimization.
- Updated user guide and current status; no server restart or live game input.

## Follow-ups

- Load updated code on hub and hauling peer at the next allowed restart, then verify live Depart values. Existing hub restart hold remains respected.
