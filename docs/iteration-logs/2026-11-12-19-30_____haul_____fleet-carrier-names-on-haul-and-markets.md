# Iteration Log

- Area: `haul`
- Title: `fleet-carrier-names-on-haul-and-markets`
- Started: `2026-11-12 19:30`

## Summary

- `/haul` and `/markets` showed fleet carriers by callsign only. They now show `NAME (CALLSIGN)` like `/routes`.

## Changes

- `GET /api/carrier-names?callsign=...` returns `{"names": {callsign: name}}` for known names, read from the store's `carrier_name` table on a hub or standalone. A peer asks the hub with the new `carrier_names` link request (502 when the hub is away).
- `/haul` asks for the callsigns on the visible route page once each (retrying after a failure) and redraws the rows and selected title when names arrive. This covers Inara results (Inara gives only the callsign, e.g. `"to_station": "Q8N-BVT"`), `/routes` imports and pasted routes.
- `/markets` asks after each list refresh and labels the list, the title, the X/Y pickers and the Best deal legs.
- Station names stay callsigns in routes and haul params, since the game navigates and docks by callsign.

## Follow-ups

- The TUI does not show carrier names.
