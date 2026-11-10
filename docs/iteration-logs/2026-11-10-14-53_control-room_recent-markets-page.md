# Iteration Log

- Area: `control-room`
- Title: `recent-markets-page`
- Started: `2026-11-10 14:53`

## Summary

- Control Room now remembers the last 10 stations whose commodities market was opened, and the web UI has a `/markets` page that browses them and finds the best deal between two of them.

## Changes

- `edap/recent_markets.py`: snapshot store keyed by MarketID, newest first, capped at 10. A revisit with a newer timestamp replaces that station and moves it to the top. The same or an older `Market.json` is a no-op, which is also how startup seeding works. Writes go through a temp file plus `os.replace`, and a corrupt store reads as empty. `commodity_key` turns `$gold_name;` into `gold`.
- `edap/market_compare.py`: pure `compare_markets(x_items, y_items, cargo_capacity)` returns X→Y and Y→X deals sorted by profit/t, plus the best round trip. A deal needs buy price and stock at the source, a sell price at the destination, and positive profit. The full hold is `min(capacity, source stock)`. Demand is shown but neither filters nor caps a deal.
- Capture: `bootstrap.load_market_json` records every changed `Market.json` into `control_room.recent_markets_file` (default `.control_room_recent_markets.json`, git-ignored). It already runs at startup, on `Docked`, and on each status refresh in the TUI and the headless server; a journal `Market` event now triggers it too.
- Server: `/markets` page plus `markets.js`, `GET /api/recent-markets` (snapshots with normalised items and the ship's cargo capacity) and `GET /api/market-compare?x=<id>&y=<id>[&capacity=<t>]`. Both use the usual token auth.
- Every web page's sidebar links to Markets, and the mobile sidebar scrolls sideways when the links overflow.

## Follow-ups

- Not tried in a real browser or a live session: the Chrome extension was offline, so only a curl smoke test against a fake-store server was done. The running server needs a restart to pick up the new routes and the capture.
- The TUI could reuse `compare_markets` for a market-deal command.
