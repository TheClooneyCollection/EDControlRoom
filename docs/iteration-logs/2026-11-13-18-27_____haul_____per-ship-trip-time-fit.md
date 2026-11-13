# Iteration Log

- Area: `haul`
- Title: `per-ship-trip-time-fit`
- Started: `2026-11-13 18:27`

## Summary

- Built step 3 of [plan 0016](../plans/0016-journal-events-and-trip-time-fit.md): the trip time model is fitted per ship from the journal event store, and `[eddn.time_model] source = "fitted"` makes `/routes` and Best deal use it.

## Changes

- `edcr/trip_time_fit.py`: `read_legs` reads legs and docked stops from the store with `json_extract` (`ShipID`, `DistFromStarLS`, `StationType`); Loadout and LoadGame of every age count, so the ship flown when the window opens is known. `fit_legs` does least squares, drops legs off by more than max(60s, 3 robust sigma) and fits again; a field with under 10 supporting legs keeps its configured value. `travel_base_s` counts only legs without a jump, since with only jump legs it cannot be told apart from `first_jump_s`. A 1e-6 ridge only keeps the matrix regular; a ridge of 1 biased the base by 5 to 8s on 36 legs.
- `TripTimeModels` holds the configured model, source and `fit_days`, refits at most once a minute, and answers `active(ship_id)` (ship, else pooled, else config) and `payload(ship_id)`.
- `[eddn.time_model] source` (`config` | `fitted`) and `fit_days` (14) in `EddnConfig.time_model_source` / `time_model_fit_days`.
- App: `time_models` replaces `time_model`. `/api/eddn-routes` and Best deal's `trip` carry `time_model` (both sets and the active one). New node read `/api/time-model`. A peer's route request carries its `ship_id`; Best deal and `/api/time-model` on a peer ask the hub (`time_model` request) and fall back to the peer's own configured model when the hub is away.
- Live store, last 14 days: 158 legs; the Panther (ShipID 9) had 126 legs and fitted docked 95, base 129, first jump 148, supercruise 15.2, surface 43; `per_extra_jump_s` stayed configured (3 two-jump legs). A 1-jump leg to a 300 Ls orbital station is 474s with docking, against 457s configured.

## Follow-ups

- Step 4: `/config` page, `POST /api/time-model` writing `config.toml` and calling `TripTimeModels.set_configured`.
- Live: restart the hub, then forge, to serve the fit.
