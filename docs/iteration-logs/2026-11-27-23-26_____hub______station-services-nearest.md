# Iteration Log

- Area: `hub`
- Title: `station-services-nearest`
- Started: `2026-11-27 23:26`

## Summary

- Built plan 0023 (M8): nearest station with a given service, as `GET /api/nearest-services` and a `/services` page. Four slices, one worktree each: A store/messages, B query and Spansh, D page, C endpoint and hub routing.
- `carriervendor` (Fleet Carrier Vendor) is confirmed lower-case from the Journal v32 manual and the EDDN `journal/1` schema; a 55 s listen of 759 live EDDN messages did not catch one.

## Changes

- `EddnStore` stores the full lower-cased `StationServices` list in additive tables `station_services_seen` and `station_service`, on its own newest-wins clock; `SCHEMA_VERSION` stays 1, Ardent and `StationTypeSeen` pass `services=None` and never wipe it, v1 snapshots import unchanged, new snapshots merge by services clock.
- `edcr/station_services.py` queries the hub and merges Spansh rows by `market_id`; `search_service` makes one Spansh request.
- `/api/nearest-services` and `/services` follow the `/cheapest` pattern (`REQUEST_NEAREST_SERVICES`).

## Follow-ups

- The full suite already ran about 1.0 ms/test on main before M8 (1344 tests in 1.36 s), over the 0.0007 s/test budget; slowest are the haul and cheapest web tests. Not caused by M8.
- A Spansh-only row can reappear when the hub excluded that station (`query_hub_services` returns only included rows).
- Try `/services` live; the VPS picks the new code up through M9 auto-update, and the tables apply on listener start.
