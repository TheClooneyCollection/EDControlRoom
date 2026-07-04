# Iteration Log

- Area: `web`
- Title: `show-inara-distance`
- Started: `2026-07-04 10:45`

## Summary

- Surfaced Inara `DISTANCE` in the haul v1 web route results instead of hiding it behind the backend payload.

## Changes

- Added a separate route-table distance column backed by `distance_from_system`.
- Added the same Inara distance to selected route details.
- Stopped using Inara distance as a fallback for route distance so the two fields remain distinct.

## Follow-ups

- Confirm live Inara result rows still have enough horizontal room after the extra distance column.
