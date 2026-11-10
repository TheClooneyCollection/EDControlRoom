# Iteration Log

- Area: `haul`
- Title: `web-route-import-surface-flags`
- Started: `2026-11-10 12:56`

## Summary

- A route pasted into `/haul` dropped any field the page did not map, and every web or selected-route haul hardcoded `station_*_on_land = false`, so surface ports (e.g. a CraterOutpost) could not be run from the web page.

## Changes

- `TradeRoute` gains `from_on_land` / `to_on_land` (default false), parsed with `route_flag_from_payload` (bool or `true/yes/1/on` text) in the server command, protocol and saved-state parsers.
- `haul_params_from_trade_route` and the web `selectedHaulParams` now pass the route's surface flags; web travel to a route endpoint inherits that endpoint's flag.
- `web/haul-ui.js`: `tradeRoutePayload` spreads the original API/pasted route first, so every pasted field survives selection; copied routes include the surface flags; route cards show `/ surface`.
- Verified with headless Chromium against the LAN page: pasting a route with `from_on_land: true` yields `station_1_on_land=true`.

## Follow-ups

- Inara results never set the flags (searches exclude surface stations by default).
- A running LAN server needs a restart before it persists the flags in the selected route.
