# Iteration Log

- Area: `control-room`
- Title: `haul-search-surface-stations`
- Started: `2026-11-10 15:41`

## Summary

- The web `/haul` route search can now include surface stations, using Inara's own three-way filter.

## Changes

- Checked inara.cz `market-traderoutes` (Chrome extension was offline, so read the form HTML): `pi4` options are `0` Yes (with Odyssey stations), `2` Yes (exclude Odyssey stations), `1` No; our existing mapping already matched.
- The server forced `use_surface_stations = "no"` for every web search. It now reads `use_surface_stations` from the payload (aliases via the shared `parse_surface_stations`, moved from `prompts.py` into `edap/inara/trade_routes.py`), rejects unknown values with `invalid_search`, saves it to `haul_search.toml`, and reports `station_carrier_only` / `use_surface_stations` truthfully.
- `web/haul-v1.html`: Surface stations select (No / Yes, exclude Odyssey settlements / Yes, with Odyssey settlements), default from `haul_search.toml` via `webDefaults.surfaceStations`; result labels say "routes" instead of "station/carrier routes" when surface is included.
- README and getting-started updated.

## Follow-ups

- Inara results never set the manual landing flag. Station type is only a sprite offset on `.stationicon` (seen: -13px Coriolis, -156px Orbis, -182px crater outpost, -780px Odyssey settlement), but the flag should not follow it: it is for stations you cannot glide close to, not surface stations. Crater outposts docked fine with it off (Chauhan Dock).
