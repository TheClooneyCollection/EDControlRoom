# Iteration Log

- Area: `control-room`
- Title: `freeze-haul-timers-on-stop`
- Started: `2026-11-07 20:33`

## Summary

- Freeze haul Session and Elapsed when routine cleanup runs, and exclude idle time between hauls.

## Changes

- Stop captures both clocks before closing the history row and clearing active state; docked cycle duration is preserved. Completed cycles retain their final Elapsed until the next cycle/haul starts instead of clearing the visible value.
- Start resumes Session from its stored elapsed duration with an explicit None check (a zero clock origin is valid), while the new run starts fresh.
- Persisted session restore and new-session resets leave idle/paused clocks frozen; active, unpaused hauling still starts the new session clock immediately. Pause/resume behavior remains covered.
- Seven fake-clock behavior tests exercise local panel rendering and remote data-source copies after common routine cleanup, repeated stops, paused stop, docked/completed cycles, relaunch, idle/paused reset, and subsequent starts including a smaller post-reboot monotonic origin.
- Full unittest discovery: 921 tests passed in 0.679s. The 0.5526s target was exceeded; the required timing report identifies existing route/haul/server/timezone tests as the slowest. This is below the previously reported ~2s baseline, so no regression is indicated.
- Iteration archive regenerated; iteration log validation and diff whitespace checks passed.

## Follow-ups

- Confirm frozen local/remote timers after a live completed, failed or operator-stopped haul. No rendering or hydrate implementation changes were needed.
