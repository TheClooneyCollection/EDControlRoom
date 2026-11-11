# Iteration Log

- Area: `haul`
- Title: `routes-surface-default`
- Started: `2026-11-10 22:36`

## Summary

- `/routes` hid every Chauhan Dock (CraterOutpost) route: the Surface stations checkbox started unchecked and the server fallback read `use_surface_stations = "yes_with_odyssey"` as off.

## Changes

- `edap/eddn/route_query.py`: `surface` goes through `_include_surface`, which reuses `parse_surface_stations` so `yes_with_odyssey` / `yes_exclude_odyssey` include surface ports and `no` excludes them; page `yes`/`no`/`1`/`0` still work through `_flag`.
- `web/routes.js`: `#route-surface` starts from `WEB_CONFIG.webDefaults.allowPlanetary` (already derived from `use_surface_stations` in `_web_form_defaults`). The page persists only the access token, so there is no saved checkbox choice to respect; a reload resets it to the haul search default.
- Tests: query fallback/override cases in `tests/test_eddn_routes.py`, served page/script wiring in `tests/test_control_room_server.py`.

## Follow-ups

- Live-check `/routes` lists Chauhan Dock routes with the default checkbox.
