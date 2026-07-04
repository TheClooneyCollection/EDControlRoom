# Iteration Log

- Area: `web`
- Title: `move-haul-actions-to-websocket`
- Started: `2026-07-04 09:09`

## Summary

- Removed Haul web action REST endpoints and moved browser search/start behavior onto the existing websocket session.

## Changes

- Removed `/api/haul/search` and `/api/haul/start` from the Starlette app; only `GET /haul` remains for serving the page.
- Added websocket `command.search_haul_routes` to the advertised protocol capabilities and JSON schema.
- Routed `command.search_haul_routes` through the websocket session handler, returning serialized route results in `response.success.result`.
- Updated `web/haul-v1.html` to consume initial/live hydrate data from websocket messages and send both search and `command.dispatch_haul_loop` through `/session`.
- Updated server tests to assert the old REST action endpoints return 404 and cover websocket search plus dispatch from a browser-style session.

## Follow-ups

- Live-check `/haul?access_token=...` against a running server and real Inara profile to validate websocket search latency and operator-role behavior.
