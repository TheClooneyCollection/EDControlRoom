# Iteration Log

- Area: `web`
- Title: `thread-websocket-haul-search`
- Started: `2026-07-04 10:21`

## Summary

- Fixed web websocket haul search failing when sync Playwright ran inside the server asyncio loop.

## Changes

- Added an async websocket message wrapper for `command.search_haul_routes`.
- Runs blocking `search_trade_routes()` through `asyncio.to_thread()` for websocket searches while leaving the synchronous handler available for direct unit tests.
- Added websocket regression coverage that verifies the search function runs outside a running asyncio event loop.

## Follow-ups

- Retry `/haul` route search against a live server with a stored browser token.
