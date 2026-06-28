# Iteration Log

- Area: `haul`
- Title: `compact-station-distance-in-route-details`
- Started: `2026-06-28 22:18`

## Summary

- Moved station-distance display into the route endpoint line so trip and hourly profit remain visible in the haul route details panel.

## Changes

- Updated Control Room route-detail rendering to append each endpoint's `STATION DISTANCE` beside the station name.
- Removed the dedicated station-distance detail row and kept the profit rows below the fold boundary.
- Refreshed the route-detail rendering test to match the new compact endpoint format.

## Follow-ups

- Live-check the route modal against longer station names to make sure the compact endpoint line still fits without clipping on smaller terminals.
