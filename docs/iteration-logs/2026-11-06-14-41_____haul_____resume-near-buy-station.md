# Iteration Log

- Area: `haul`
- Title: `resume-near-buy-station`
- Started: `2026-11-06 14:41`

## Summary

- Starting two-way haul in normal space near station 1 with an empty hold used to return `DEPART_STATION_1_SYSTEM`, so the ship flew empty to station 2 (same for station 2). It now docks at that station and buys first. The user chose this behaviour.

## Changes

- `_detect_start_phase`: in normal space, depart only with a full load or when that station has no buy commodity. Otherwise return to the station when the latest relevant journal event shows the ship is near it (`Undocked`, `DockingRequested`, `DockingGranted` for that station, or a `SupercruiseExit` at that station). Elsewhere in normal space it returns an error asking the operator to enter supercruise.
- `detect_transit_resume_state`: `Undocked` from the destination station now means `POST_DROP_NEAR_STATION`, so `dock()` requests docking straight from normal space.
- `haul_loop_two_way`: an initial `TRANSIT_TO_STATION_1` runs as a pre-cycle step, so `iterations=N` now gives N full cycles. A start-phase error result is returned instead of crashing on `.name`.
- Tests cover both stations, partial load, full load, no buy commodity, far-from-station error, `Undocked` resume, and the iteration count.

## Follow-ups

- Live-validate the near-station resume and docking request in CrossOver.
