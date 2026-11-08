# Iteration Log

- Area: `web`
- Title: `route-copy-paste`
- Started: `2026-11-08 11:43`

## Summary

- Haul search scrapes Inara through Playwright and Chrome. The Steam Deck should not need either, so a route is now searched on the laptop's Control Room and pasted into the Deck's.

## Changes

- Haul v1 setup panel: a `Copy / paste route` disclosure with a text box, `Copy selected` and `Import pasted`. Scope per the user: the selected route only, route fields only (no search form parameters), haul page only (not `/multi-haul`).
- Copy writes `routeTransferPayload(route)` as pretty JSON: the 11 route fields a haul needs or shows (systems, stations, commodities, station and route distances, profits), empty ones dropped. Index, `raw_text`, `url_links`, supply/demand snapshots and `distance_from_system` stay local; `raw_text` only feeds a debug log on search load. Older pasted JSON with those fields still imports. The Clipboard API needs https or localhost, so a LAN `http://` page falls back to `execCommand("copy")`, then to leaving the text selected for Ctrl+C.
- Import requires from/to systems and stations, keeps the index of a matching local route (same `routeKey`) or takes a fresh one, then selects it and persists it with the existing `command.select_trade_route`, which validates the route server side. No new server command.

## Verification

- Full suite passes. A node round trip of the real `routeFromApi` → `tradeRoutePayload` → JSON → `routeFromApi` gives identical fields and the same `routeKey`. Confirmed live 2026-11-08 by the user: copied on the laptop Control Room, pasted into the Steam Deck one.
