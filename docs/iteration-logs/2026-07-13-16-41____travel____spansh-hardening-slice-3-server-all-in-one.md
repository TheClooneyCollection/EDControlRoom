# Iteration Log

- Area: `travel`
- Title: `spansh-hardening-slice-3-server-all-in-one`
- Started: `2026-07-13 16:41`

## Summary

- Plan 0013 slice 3. All-in-one retry/wait/compare moved off the browser and behind a new WS command `command.dispatch_route_all_in_one`. Server now composes the same primitives the two REST endpoints already use, so any client (web, TUI, Python) gets the same behavior with one call.

## Changes

- `edap/control_room/server/app.py`: extracted `RouteCompareError`, `fetch_and_cache_spansh_route`, and `build_and_cache_live_comparison` as module-level helpers. Refactored `/api/route-compare` (live branch) and `/api/spansh-route` to delegate to them. New async handler `_handle_dispatch_route_all_in_one_async` sequences: `command_handler.dispatch_destination(...)` -> `fetch_and_cache_spansh_route(...)` -> loop `asyncio.sleep(navroute_wait_seconds)` + `build_and_cache_live_comparison(...)` with `RouteCompareError.retryable` gating retries. Response includes `route_id`, comparison payload, and a `phases[]` trail so clients can render a checklist. `journal_dir` + config defaults threaded through `_receive_session_messages` and `_handle_session_message_async`.
- `edap/control_room/protocol/capabilities.py` + `docs/schemas/control_room_message.schema.json`: registered `command.dispatch_route_all_in_one` and its payload schema.
- `web/route-compare.js`: `allInOne()` collapsed to a single `sendCommand("command.dispatch_route_all_in_one", ...)` call. Also fixed pre-existing bug in `dispatchDestination()` where `galaxy_map_settle` was missing from the payload (would have been rejected by the WS handler).
- `web/haul-ui.js`: exposed `galmapSettleTime` on `window.EDCR_HAUL` so `route-compare.js` can share the same source of truth.
- `tests/test_route_compare_endpoint.py`: new `DispatchRouteAllInOneTests` covers happy path (verifies dispatch_destination is called on the command handler and phases include ok for each step), retry-then-succeed (404 retryable twice then ok, verifies attempt count and phase statuses), all-attempts-fail (returns `route_all_in_one_compare_failed` error code), missing `from` (returns invalid_command), and no command_handler (transport_unavailable). Uses ws bridge via `TestClient.websocket_connect`.

## Follow-ups

- Slice 4: Active route panel on `/haul`.
- Live-validate the end-to-end all-in-one command under CrossOver/macOS.
