# Iteration Log

- Area: `web`
- Title: `server-route-selection-hydrate`
- Started: `2026-07-04 18:20`

## Summary

- Server now retains the current web-selected and last accepted running Inara trade route in broker-owned server state so `/hydrate` and websocket hydrate can restore it after web reload/reconnect.

## Changes

- Added `selected_trade_route` / `running_trade_route` to the Control Room data read model and data-message round trip.
- Added websocket `command.select_trade_route`; web selection changes send the selected route, and `command.dispatch_haul_loop` can carry the started route.
- Updated `/haul` to merge hydrated selected/running routes into its route table and prefer the running route when both are present.

## Follow-ups

- Live-check multi-client behavior during web route search/start so route selection updates feel natural when more than one browser is connected.
