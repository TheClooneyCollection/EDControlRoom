# Iteration Log

- Area: `control-room`
- Title: `hub-roles-and-one-station-store`
- Started: `2026-11-11 12:33`

## Summary

- Plan 0015 step 1 (roles and data ownership), on `feat/hub-command-centre`. `[hub] role` = `standalone` (default) | `hub` | `peer` decides who owns data: hub and standalone always open the market SQLite store (`edap/market_db.py`), a peer never does. `[eddn] enabled` only starts the listener, and never on a peer.
- The store's `system` and `station` tables are the one station facts store. Writers, newest wins: EDDN, the local journal (`FSDJump`/`Location`/`CarrierJump` StarPos, `Docked` and docked `Location` distance, type and pads, parsed by `journal_event_updates` the same way EDDN parses uploads), our Market.json station type (`StationTypeSeen`, written with our markets by `import_game_markets`; a new row needs the system's address from the `system` table, so a market in a never-visited system adds no type), and Ardent (`EddnStore.save`).
- `places` is gone from the recent markets file; Best deal (`/api/market-compare`) reads the store, then Ardent. `trip.stations.*_source` is now `store` or `ardent`.

## Changes

- `ControlRoomApp` and `HeadlessControlRoomHost` take a required `record_station_facts`; bootstrap replays the latest journal into it. The TUI-only mode opens the store by role too; `connect` passes an explicit drop.
- `start_eddn_service` takes the server's store and no longer closes it; our markets import (`import_game_markets_every`, thread `game-markets`, log prefix `Market DB`) runs on every hub/standalone, not only with EDDN on.
- Peer: Best deal returns `trip.hint` ("Station facts come from the hub.") and `/markets` shows it instead of the missing list; `/api/eddn-routes` without a hub URL says the hub serves routes. Old peer HTTP forwarding is untouched (step 2 replaces it); it now needs `role = "peer"`, and `url` with another role is a config error.
- EDDN `Location` messages with `Docked: true` now also write the station row.

## Follow-ups

- Step 2: send a peer's journal facts and markets up the link, answer Best deal facts over it.
