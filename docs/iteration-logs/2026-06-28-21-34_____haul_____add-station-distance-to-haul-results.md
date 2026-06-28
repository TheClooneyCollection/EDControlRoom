# Iteration Log

- Area: `haul`
- Title: `add-station-distance-to-haul-results`
- Started: `2026-06-28 21:34`

## Summary

- Added both Inara `STATION DISTANCE` values to haul route results so the picker can show how far each endpoint station is from its star.

## Changes

- Extended `TradeRoute` and snapshot serialization to carry `from_station_distance` and `to_station_distance`.
- Updated the haul route label/detail rendering to show compact station-distance summaries and explicit per-endpoint station-distance rows.
- Added parsing and snapshot tests to keep local and remote route pickers in sync.

## Follow-ups

- Live-validate that Inara always emits the source station distance first and the destination station distance second across alternate trade-route card layouts.
