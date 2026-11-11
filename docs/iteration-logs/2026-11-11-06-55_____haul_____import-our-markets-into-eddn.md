# Iteration Log

- Area: `haul`
- Title: `import-our-markets-into-eddn`
- Started: `2026-11-11 06:55`

## Summary

- Our own captured markets (the recent-markets file recorded from `Market.json`) now feed the local EDDN DB, so `/routes` sees stations we docked at even when nobody uploaded them.

## Changes

- `edap/eddn/messages.market_snapshot_from_game` turns a recorded market into the same `MarketSnapshot` an EDDN commodity message parses to: `$silver_name;` becomes `silver`, the same tradeable-row filter applies, and the game's own timestamp is kept.
- Newest wins through the existing store rule: a snapshot older than the stored `updated_at` is skipped; a newer one replaces the whole station (one `updated_at` per market, so merging would let old rows pose as fresh; this is also what EDDN does).
- `edap/eddn/game_markets.import_game_markets` applies all recorded markets and commits; `tools/eddn_import_markets.py [--db] [--recent-markets]` runs it by hand.
- With `eddn.enabled`, the server starts thread `eddn-game-markets`, which imports at start and whenever the recent-markets file changes (polled every 5 s), logging `EDDN our markets: ...`.
- Name check before the change: Chauhan Dock, Sitterly Enterprise and The Job Centre names all matched the DB. Sitterly's EDDN entry had 6 sell-only salvage rows (escape pods, black boxes) that are absent from our `Market.json`; whole-station replacement drops them.
- Manual run 2026-11-11: Sitterly Enterprise written (ours 06:34 vs DB 04:43); Chauhan Dock and The Job Centre kept (DB newer).

## Follow-ups

- The running server picks up the watcher only after a restart.
- Station and system details from the journal are out of scope; only market prices are imported.
