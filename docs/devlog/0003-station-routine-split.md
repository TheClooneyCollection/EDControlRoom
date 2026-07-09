# Devlog 0003: Station Routine Split

## Summary

On 2026-07-09, a live-use expectation clarified the direct `dock` command behavior:

- If the ship is in supercruise, `dock` should wait for `SupercruiseExit`.
- If the ship is already in normal space, `dock` should start docking attempts immediately.

The minimal fix was made in the Control Room direct station command launcher. It does not change haul or travel transit behavior.

## Current Split

Station routines are centralized at the primitive level:

- `edap.routines.docking.dock()` owns the station approach sequence: optional `SupercruiseExit` wait, boost, docking request, docking response, `Docked`, and optional refuel/repair.
- `edap.routines.docking.undock()` owns the station departure sequence: launch menu, `Undocked`, then `NoTrack` or carrier `Exploration` clear-of-station confirmation.

The split is in orchestration:

- `edap.control_room.routines_station` is the direct typed-command launcher for `dock` and `undock`.
- `edap.routines.transit` wraps the same docking primitives for haul, multi-leg haul, and travel. It adds route setup, resume-state detection, hyperspace arrival handling, navigation-panel handoff, on-land manual landing handoff, pending journal-event carryover, and interdiction abort behavior.

## Why They Are Not Fully Unified

Direct station commands and transit flows answer different questions:

- Direct `dock`: "Given the current Control Room ship status, should we wait for drop or request docking now?"
- Transit `dock`: "Where are we in a route/resume flow, did we already arrive/drop, should we open nav, abort, or hand off for manual landing?"
- Direct `undock`: "Launch and wait until control is safely clear of the station."
- Transit `undock`: "Launch, set the route after `Undocked`, wait until clear, then escape mass lock."

Merging all of that into one large routine would make the primitive harder to test and would couple direct manual commands to haul/travel policy.

## Fix Applied

`edap.control_room.routines_station._should_wait_for_supercruise_exit()` now makes the direct command policy explicit:

- wait for `SupercruiseExit` only when status is `in_supercruise` or the legacy spelling `supercruise`
- otherwise start the docking sequence immediately

Regression coverage asserts both supercruise and normal-space direct-command behavior.

## Follow-Up

The next cleanup should keep the primitive/orchestration split, but move shared station command policy into a small neutral helper so direct Control Room commands and transit wrappers do not grow parallel state predicates.
