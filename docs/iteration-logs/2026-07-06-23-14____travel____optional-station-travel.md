# Iteration Log

- Area: `travel`
- Title: `optional-station-travel`
- Started: `2026-07-06 23:14`

## Summary

- Made station optional for the new travel command and structured web/socket dispatch.

## Changes

- `travel <system>` now parses and dispatches as system-only travel; `travel <system> / <station>` keeps the station docking path.
- Added system-arrival completion for stationless travel so the routine stops after destination-system arrival instead of calling station docking.
- Updated `/haul` Travel Assist with a visible secondary Clear button, optional station validation, stationless raw command dispatch, and dirty-state handling so cleared station text is not re-filled by selected-route rendering.

## Follow-ups

- Live-validate system-only travel from docked, normal-space, supercruise, and remote-system starts under CrossOver/macOS.
