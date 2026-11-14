# Iteration Log

- Area: `control-room`
- Title: `best-deal-uses-eddn-store-prices-when-newer`
- Started: `2026-11-14 20:43`

## Summary

- Live 2026-11-14: the `/markets` Best deal panel showed Chauhan Dock <-> Sitterly Enterprise at 39,752 Cr/t (Silver / Insulating Membrane) from our own Market.json visit of 2026-11-13 21:21, while the hub's EDDN store had seen Chauhan Dock at 19:29 on the 14th with the whole-market discount over. Best deal read only `.control_room_recent_markets.json`; the store was used for routes and station facts, never for prices.
- Now each market's prices are the newer of our visit and the EDDN store (newest wins per market; a store row at the same instant is our own import, so the visit wins). With live data the pair drops from 49,721 Cr/t (visit only) to 4,344 Cr/t.

## Changes

- `edcr/market_db.py`: `StoredPrices` and `read_stored_prices(database_file, market_ids, display_names)` read `market.updated_at` and `price` rows read-only; EDDN rows carry only commodity keys, so names come from our own visits where known.
- `edcr/market_compare.py`: `PricedMarket`, `snapshot_epoch`, `pick_prices(snapshot, stored)`; sources `visit` and `eddn`.
- `/api/market-compare` compares the picked prices and adds `prices: {x, y, hint}` (`market_id`, `source`, `prices_at` ISO UTC). Hub and standalone read their store; a peer asks the hub with the new `market_prices` link request (`answer_market_prices`), and falls back to its visits with the hub-unreachable hint when the link is down; a peer without a hub says `EDDN prices come from the hub.`
- `web/markets.js` shows `Prices: <X> from EDDN 1 h ago · <Y> from your visit 10 h ago.` under the Best deal result (`priceSources`). The station list and the commodity table still show the visit snapshot.
- Tests: `test_market_compare_uses_the_eddn_stores_newer_prices_for_a_market` (server, store newer for X and older for Y, no store) and `test_best_deal_prices_come_from_the_hub_store_when_newer_than_the_visit` (hub + peer, link drop, bad body). Full suite 1203 tests in 0.65 s.
- v1.39.0 was released earlier this session (haul start refusal, fitted trip times, server logs); this change is after the tag.

## Follow-ups

- The hub needs a restart to serve this; the market list ages and the commodity table could also take the newer store prices.
- The Inara headless search on the hub is still blocked by Inara's access check (fingerprint, not a cookie); our own `/routes` from the EDDN store is the working path.
