# Iteration Log

- Area: `web`
- Title: `wire-haul-routine-and-activity`
- Started: `2026-07-04 09:27`

## Summary

- Connected the Haul web routine and activity panels to backend websocket hydrate/event data.

## Changes

- Added derived `routine.haul_phase` to the Control Room data read model so browser clients can render the active two-way haul phase without duplicating low-level routine internals.
- Preserved `haul_phase` through hydrate serialization/parsing and fixed activity-log parsing to accept serialized tuple entries.
- Added live haul cargo-moved telemetry from MarketBuy journal counts and reset it when a new haul session starts.
- Updated `web/haul-v1.html` to render routine step state, elapsed/current-run/cargo metrics, routine status, hydrate activity history, and appended activity events from websocket data.
- Removed static sample activity rows and static routine status copy from the web page.
- Added data-message coverage for `haul_phase` and hydrated activity entries.

## Follow-ups

- Live-check the derived haul phase labels against a real two-way run and refine phase mapping if operator-visible transitions need more precision.
