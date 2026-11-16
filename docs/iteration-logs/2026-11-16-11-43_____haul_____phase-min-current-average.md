# Iteration Log

- Area: `haul`
- Title: `phase-min-current-average`
- Started: `2026-11-16 11:43`

## Summary

- User asked this worker to take charge while main/secondary were unavailable and add Min/Curr/Avg to each of the five haul phase cards; confirmed current-session scope.

## Changes

- Added pause-aware phase timing on the haul session clock, using actual assisted two-way phase callbacks. Buy/Undock/Depart name the source station; Transit/Sell name the destination, so samples are grouped by destination direction and completed stages stay on the same displayed leg.
- Current updates from normal server hydrates; minimum/average use completed stage samples only. Repeated callbacks do not restart the clock or count samples; pause/stop freezes; an unobserved interrupted finish is not sampled. New session, changed route or changed ship clears the appropriate timing state.
- Saved session checkpoints retain samples and frozen elapsed values without persisting process clock origins. Resumed partial stages after relaunch/new-session are excluded from minimum/average. Track only and legacy peers show missing values rather than inferred stage durations.
- Added `routine.haul_phase_timings` through local read models and protocol decode. Web cards display mm:ss or h:mm:ss, em dash for missing values, and sample-count tooltips. No browser extrapolation, game inputs or automation changes.
- UI delegated in its own worktree and committed, integrated linearly; agent dismissed and worktree removed. Backend/session/persistence integration done locally because those changes share state ownership.
- Full suite: 1286 tests in 1.107 s, OK (1 skipped), using the repo uv environment; existing localhost HTTP test needs escalation. Required timing report run because the 0.7716 s suite budget is exceeded, as before; leading hotspots remain the Node web flow and four existing transit tests.
- Behavior tests cover independent directions, repeat callbacks, completion-only samples, pause/resume/stop, session reset, state roundtrip/relaunch, changed route/ship and malformed old state. Existing Node flow covers actual UI render, missing/old-peer values, frozen pause, current refresh, direction change and duration formatting.
- Chromium rendered shipped card HTML/CSS with fixture values at 1440 and 390 px; screenshots reviewed, no horizontal overflow (`/private/tmp/edcr-phase-times-1440.png`, `-390.png`). Syntax/diff checks pass. No live hub/game mutation or server restart.

## Follow-ups

- Hub restart remains on hold. Updating the hub UI alone cannot produce timings from an older forge process; load the new code on both hub and hauling peer at the next permitted restart.
- Live-check advancing Curr, pause freezing and return-leg samples after deployment. Existing journals do not contain these stage transition intervals, so there is no historic backfill; Min/Avg fill from newly completed stages.
