# Iteration Log

- Area: `haul`
- Title: `add-inara-distance-and-500-route-default`
- Started: `2026-06-28 21:02`

## Summary

- Added Inara `DISTANCE` parsing to haul route data and surfaced it in the Control Room route picker.
- Raised the default Inara max route distance from `60` to `500` Ly for generated haul searches and pasted-URL expectations.

## Changes

- Extended `TradeRoute` plus snapshot serialization/deserialization to carry `distance_from_system`.
- Updated route-picker label/detail rendering so operators can see current-system distance separately from route distance.
- Refreshed Inara and Control Room tests for the extra field and the new default search parameter.

## Follow-ups

- Live-validate that the Inara scraper still captures `DISTANCE` consistently across alternate route-card layouts and no-location searches.
