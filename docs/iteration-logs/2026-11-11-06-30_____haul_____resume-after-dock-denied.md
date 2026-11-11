# Iteration Log

- Area: `haul`
- Title: `resume-after-dock-denied`
- Started: `2026-11-11 06:30`

## Summary

- Restarting a haul that stopped on exhausted dock retries now sends a new dock request instead of waiting for `Docked`.

## Changes

- Why: Elite logs `DockingRequested` before `DockingDenied`, and `detect_transit_resume_state` skipped the denial, so the restart saw a pending request, logged "Docking already in progress" and waited out the dock timeout.
- `DockingDenied`, `DockingTimeout` and `DockingCancelled` for the destination station now resolve to `POST_DROP_NEAR_STATION`, which skips the drop wait and requests docking again; for another station they resolve to `NONE`.
- Restarting no longer splits the run. Before, the failed run was written `aborted` and the restart became a `partial_start` run aborted at the next station 1 departure, so the trip counted only in the all-in Total.
- `clear_routine` now calls `suspend_haul_stats` for a two-way haul: with a run in progress it freezes timers as a pause does, snapshots the duration, and marks the stats `suspended` instead of aborting. `start_haul_stats` with the same stations and commodities continues that run; a different haul, `clear` or a relaunch still aborts it, and a different haul starts a fresh session. Multi-leg haul and an end with no run in progress still stop as before. Stop now also suspends, so a stop then restart of the same haul is one run too.

## Follow-ups

- No live validation yet of a restart after a pad-full or other denial.
- Journal events while suspended (e.g. a manual dock) are not recorded, since tracking only runs while the haul is active; trades are made by the restarted haul, so money is unaffected.
- A relaunch still aborts an open run; keeping it across relaunch would need the clean-run fields in saved state.
