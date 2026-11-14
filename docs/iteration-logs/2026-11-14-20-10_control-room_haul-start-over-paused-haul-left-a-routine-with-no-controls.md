# Iteration Log

- Area: `control-room`
- Title: `haul-start-over-paused-haul-left-a-routine-with-no-controls`
- Started: `2026-11-14 20:10`

## Summary

- Live 2026-11-14: a hub page looking at a Windows peer showed the peer's haul activity (dock requests) but Resume, Pause, Stop after run and Stop now stayed disabled. The peer's hydrate had `routine_active: false` and no routine name while the haul loop ran; the hub relayed that state faithfully.
- Cause: a haul had paused at station 1 (15:34 UTC, waiting for `resume`); at 19:41 Start route from the page ran `command.dispatch_haul_loop` -> `dispatch_haul_loop`, which, unlike the TUI `haul` command, never checked `check_routine_ready`. The new routine set `routine_active` and a new worker; `_run_in_thread` is `@work(..., group="routines", exclusive=True)` (the headless host inherits the Textual `App`, so Textual's worker manager runs routines on hub and peer too), so Textual cancelled the paused worker, whose `clear_routine` then cleared `routine_active`, the worker handle and the routine name, and suspended the haul stats, all under the new haul. The new haul ran on with no stop (Stop now answered "no active routine to cancel") until it failed on docking retries at 19:59.

## Changes

- `dispatch_haul_loop` now calls `check_routine_ready` before building the runtime (after the Track only branch, which refuses on its own): a Start over a running or paused haul is refused as `A routine is already running`, bumping `busy_refusals`.
- `clear_routine(app, worker)` takes the worker that finished and leaves the state alone when `_routine_worker` is a newer one; `run_routine_thread` passes `get_current_worker()`, `app._clear_routine()` passes None (unconditional).
- Tests: a paused haul refuses a second dispatch and keeps its pause flags; a replaced worker leaves the newer routine's state; a finished worker still clears its own. Full suite 1201 tests in 0.65 s.
- Checked live read-only: `/api/nodes` on the hub and a look-only `?node=` websocket session gave the peer's role (`active_operator`) and hydrate.

## Follow-ups

- The headless host still inherits the Textual `App` for its worker machinery; moving routines onto a plain thread runner would drop that dependency on hub and peer (separate refactor).
- The run left open by the 19:59 docking failure continues when the same haul is started again.
