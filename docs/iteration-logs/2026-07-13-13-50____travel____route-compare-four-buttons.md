# Iteration Log

- Area: `travel`
- Title: `route-compare-four-buttons`
- Started: `2026-07-13 13:50`

## Summary

- Split the Route Comparison panel action row into four buttons per user request: **Set in-game route**, **Fetch Spansh**, **Compare**, **All in one**. The Compare-only workflow is preserved. Fetch Spansh lights up Switch to Spansh without needing a local NavRoute.json, so the operator can plan Spansh hops before the game has plotted anything.

## Changes

- `edap/control_room/server/app.py`: new `/api/spansh-route` endpoint. Reuses `edap.spansh_router.plot_route` on a worker thread, caches the returned route via `broker.server_state.cache_spansh_route` under a `RouteRequestKey`, returns `{spansh, route_id}`. No NavRoute read, no announcement (that stays on `/api/route-compare`). Query params match the compare endpoint (`from`, `to`, `range`, `efficiency`, `supercharge_multiplier`).
- `edap/routing/web.py`: renamed `_route_payload` -> `route_payload` (public) so the new endpoint can serialize a single Spansh route without duplicating the metadata switch.
- `web/haul-v1.html`: replaced the four-button row with Set in-game route, Fetch Spansh, Compare, All in one, and moved the fixture loaders onto their own ghost row. Switch to Spansh keeps its previous ghost-until-primary treatment.
- `web/route-compare.js`: added `dispatchDestination()` (sends `command.dispatch_destination` with the To system), `fetchSpanshOnly()` (calls `/api/spansh-route` and renders the Spansh side via new `renderSpanshOnly()`), and `allInOne()` (dispatch destination -> fetch spansh -> 6s wait -> full compare). Compare button unchanged. Switch button state derives from `state.lastRouteId` via a shared `updateSwitchButton()` helper.
- `tests/test_route_compare_endpoint.py`: new `SpanshRouteEndpointTests` class covers cache + route_id, missing param 400, invalid numeric 400, plot_route failure 502, and auth 401. Uses `unittest.mock.patch` on `edap.control_room.server.app.plot_route` so no live Spansh calls.

## Follow-ups

- Live-validate the four-button flow under CrossOver/macOS.
- Retry orchestration currently lives in the browser; user has asked to move that to the server so all clients get the same behavior. Tracked in a new plan doc.
- Spansh dispatch today only sets the destination; user wants it to undock + boost away like `travel`. Same plan doc.
- `destination_set` TTS is firing between waypoints (after a hyperspace jump) not only when actually setting a destination — likely another emitter is reusing the id. Same plan doc.
- Need an "Active route" panel mirroring the active haul routine card: last waypoint → X systems → current system → Y more systems → next waypoint. Same plan doc.

## Config + retry v2

- Added `control_room.route_compare_navroute_wait_seconds` (default `6.0`) and `route_compare_compare_retry_attempts` (default `3`) to the TOML defaults, `ControlRoomConfig`, and `serve_observer_mode` wiring.
- New `GET /api/route-compare/config` returns the two values. Web UI fetches on init, prefills the new inputs, and the `allInOne` flow now loops compare with retry on 404 / errors.
- User feedback after ship: retries should be on the server; keeping this client-side is a stopgap. Follow-up plan will move retry orchestration to the server so any client gets the same behavior.
