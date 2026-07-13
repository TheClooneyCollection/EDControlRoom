# Iteration Log

- Area: `travel`
- Title: `spansh-hardening-slice-4-active-route-panel`
- Started: `2026-07-13 16:59`

## Summary

- Plan 0013 slice 4. New Active route panel on `/haul` shows `last waypoint -> X systems -> Current -> Y more systems -> next waypoint` while a Spansh route is running. Backend persists the active `route_id` on `ControlRoomServerState`; hydrate exposes an `active_spansh_route` payload containing the cached route so any client can render progress.

## Changes

- `edap/control_room/server/state.py`: `set_active_spansh_route(route_id)` and `active_spansh_route_id()`.
- `edap/control_room/server/app.py`: `_server_hydrate_data` now injects `active_spansh_route = {route_id, route: route_payload(...)}` (serialized via existing `route_payload` helper) when the broker has an active id. `dispatch_spansh_route` handler now calls `set_active_spansh_route(route_id)` and `_publish_route_hydrate(...)` on success so all observers see the panel light up. Registered `active-route.js` in the asset allowlist.
- `edap/control_room/dependencies.py` + `edap/control_room/protocol/data_messages.py`: new `active_spansh_route: dict | None = None` field on `ControlRoomDataReadModel`, parsed back in `data_read_model_from_payload`.
- `web/haul-v1.html`: new `#active-spansh-panel` section (`.route-compare-full` styling, initially `.hidden`) inserted between the routine card and Route Comparison. Registers `active-route.js`.
- `web/active-route.js`: subscribes to `edcr:hydrate` and `edcr:ship-state`. Locates `ShipState.system` in the cached route's waypoints, renders last/current/next plus the systems-behind / systems-ahead gaps and a `Spansh · N jumps · M boosts · Kx FSD` summary. Falls back to `off route` when the current system is not part of the waypoint list.
- `web/haul-ui.js`: expose `window.EDCR_HAUL.lastHydrate` and dispatch `edcr:hydrate` after each hydrate so `active-route.js` (and future panels) can react without re-parsing the WS stream.
- `web/haul-ui.css`: minimal `.active-spansh-*` styling for the flex row.
- `tests/test_route_compare_endpoint.py`: `ActiveSpanshRouteHydrateTests` covers the empty case (`active_spansh_route` is `None`) and the round-trip (dispatch caches route + sets active id, subsequent hydrate exposes route_id and waypoint list).

## Follow-ups

- Consider surfacing route completion / cancellation on the panel (currently the active route stays visible until another one is dispatched).
- Live-validate the panel under CrossOver/macOS on a real Spansh run.
