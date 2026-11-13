# Iteration Log

- Area: `control-room`
- Title: `haul-edcr-profit-per-hour-and-inara-check-hint`
- Started: `2026-11-13 23:17`

## Summary

- Searches from a phone over Tailscale showed no results. The hub log showed every search at 23:01-23:03 failing with Inara's access check in the headless Playwright browser. Tailscale was not involved. The page only said "Search failed" in the header, and the detail went to the Activity log.
- `/haul` now says why a search failed, in the results table. Profit / hr also shows EDCR's own estimate beside Inara's.

## Changes

- `edcr/inara/trade_routes.py`: `InaraAccessCheck(RuntimeError)` is raised for the headless access check.
- `edcr/control_room/server/app.py`: the search maps it to `inara_access_check`. The message names the host (`socket.gethostname()`) and the `tools/scratch/scratch_inara_trade_routes.py --show-browser '<query url>'` command, which shares the Playwright profile with the headless searches. A peer relays the hub's message with its `Hub <label>:` prefix.
- `POST /api/haul-trips` (body `{"routes": [...]}`, at most 100) estimates each route's round trip for `viewed_ship`. It uses the same station facts (`read_station_facts`, extracted from Best deal's `read_trip`, so a peer asks the hub) and the same active time model. It returns `trip_s`, `profit_per_hour` (Inara's profit per trip over EDCR's trip time), `inara_profit_per_hour`, `inara_trip_s` (Inara's per trip over per hour), the ship and a hint.
- `edcr/trade_trip.py`: `store_lookup` falls back to station + system name when the market id is unknown (Inara gives none). `with_inara_dist_ls` fills a missing distance from Inara's `"1,080 Ls"`. `route_profit_per_hour` was added.
- `web/haul-ui.js`: the Profit / hr cell shows `Inara: <Cr/h> <m/trip>` above `EDCR: <Cr/h> <m/trip> (<ship name>)`. When EDCR has no estimate, the row lists what is missing. Estimates are cached by route key and cleared on each new search. A failed search empties the table and shows `Search failed: <message>`.
- In-process check against the real `.eddn_markets.sqlite3` with the saved Chauhan Dock ↔ Sitterly Enterprise route: EDCR 602 s / 270.3M Cr/h against Inara's 602 s / 270.1M, in 13 ms. The running hub was not restarted, so the page itself is unchecked live.

## Follow-ups

- Restart the hub so it serves this, then check `/haul` on a phone.
- The access check fix still needs someone at the hub's screen. A Control Room button that opens the visible browser there could come later.
