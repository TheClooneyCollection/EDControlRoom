# Iteration Log

- Area: `haul`
- Title: `allow-any-station-distance`
- Started: `2026-06-27 14:17`

## Summary

- Added operator-facing `any` support for Inara haul-search max station distance so Control Room no longer requires raw `0` for the "Any" INARA option.

## Changes

- Updated the haul search prompt parser to accept `max_station_distance_ls=any` and keep the saved/replayed value as `any`.
- Normalized Inara trade-route query handling so Control Room emits `pi9=0` for `any` and maps pasted `pi9=0` URLs back to `any`.
- Added unit coverage for prompt submission and INARA URL build/parse behavior, then reran the full unittest suite successfully in `0.289s`.

## Follow-ups

- Live-validate the `any` station-distance path against a fresh INARA fetch in the operator UI when the next CrossOver trading session runs.
