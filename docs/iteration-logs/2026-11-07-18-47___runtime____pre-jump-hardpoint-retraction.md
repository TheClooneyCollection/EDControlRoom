# Iteration Log

- Area: `runtime`
- Title: `pre-jump-hardpoint-retraction`
- Started: `2026-11-07 18:47`

## Summary

- Prevent routine-driven FSD engagement while readable Status.json still reports deployed hardpoints after two retraction attempts.

## Changes

- Added one shared function with injected status read, toggle, time, sleep and progress capabilities; uses semantic `DeployHardpointToggle` binding support through controls/progress controls and binding diagnostics.
- Covers `jump` (control room and CLI), shared undock/normal-space departures for travel, two-way haul, multi-leg haul and Spansh start handoff, plus travel from supercruise. Manual pilot-driven Spansh hops remain manual.
- Added `[controls.hardpoints].retract_timeout_seconds` (positive finite, default 5s), 0.1s polling and one paced retry. Confirmed persistent deployment returns a routine failure with the usual Failed:/Try: operator guidance.
- User-approved hybrid policy: unavailable/empty/corrupt status retries within the timeout, warns and continues; unknown state never triggers a toggle. Mass-lock escape also tolerates malformed status so it reaches the guard. Explicit Flags validation is opt-in for pre-jump reads, preserving existing balance/cargo consumers.
- Full suite: 914 tests passed in 0.993s; timing budget is 0.5484s (0.0006s/test), so the required slowest-test report was run. Existing CLI/server/journal tests dominate; the timing target remains unmet on this machine.
- Added behavior coverage for successful retraction, second-press recovery, persistent deployment, missing binding, transient/persistent unreadable state, semantic dispatch, config validation, and all three travel start paths.

## Follow-ups

- Live-validate under CrossOver, especially Status.json refresh latency and a dropped toggle; tune the configurable timeout if needed.
- Landing gear and cargo scoop are intentionally outside this slice. No raw key is used.
- The legacy `tools/run_routine.py --routine haul_loop` still has pre-existing stale flat HaulRuntime/HaulTiming construction; its standalone jump entry was updated, but repairing legacy haul CLI is separate work.
