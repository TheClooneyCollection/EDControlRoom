# Iteration Log

- Area: `runtime`
- Title: `timing-randomization`
- Started: `2026-06-29 08:24`

## Summary

- Added shared timing randomization for human-like delays, holds, and typing cadence, then tightened the runtime APIs so production callers must pass an explicit timing sampler instead of relying on optional `None` paths.

## Changes

- Added `edap.timing` with a config-backed clamped log-normal sampler plus a no-jitter helper for deterministic tests.
- Added `[timing]` defaults in `defaults/timing.toml`, loaded them through `edap.config`, and exposed the sampler on `RuntimeContext`.
- Routed runtime input controllers, `ShipControls`, Control Room delayed-command sleeps, and routine CLI sleepers through the shared timing sampler.
- Added `docs/operators/input-timing.md` plus README/docs index links so operators can tune the timing model without reading the code.
- Updated input, runtime, config, CLI, and Control Room tests to pass explicit timing samplers and cover the new config/default behavior.

## Follow-ups

- Live-tune the default delay/hold/typing distribution against real CrossOver sessions so the human-like jitter remains believable without destabilizing menus.
