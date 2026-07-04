# Iteration Log

- Area: `web`
- Title: `persist-route-selection-state`
- Started: `2026-07-04 18:29`

## Summary

- Selected and running web trade routes now persist through the existing Control Room state file so `/haul` can hydrate the route after a server restart.

## Changes

- Added `selected_trade_route` and `running_trade_route` to `ControlRoomState` load/save serialization.
- Headless websocket route selection/start commands now write route state through `persist_trade_route_state()`.
- `serve` seeds broker route state from the loaded state file before exposing hydrate/session routes.

## Follow-ups

- Live-check restart recovery after selecting and after starting a route to verify the restored web table matches operator expectations.
