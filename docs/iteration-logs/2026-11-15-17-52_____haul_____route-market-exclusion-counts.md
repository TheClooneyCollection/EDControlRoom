# Iteration Log

- Area: `haul`
- Title: `route-market-exclusion-counts`
- Started: `2026-11-15 17:52`

## Summary

- Explain excluded route markets in the API and status line without changing search behavior or existing call signatures.

## Changes

- Added `load_route_market_selection`; `load_route_markets` remains a list-returning wrapper. `run_route_query` includes `markets_left_out` beside `markets_considered`.
- Each market counts against its first failed filter: age, coordinates, carriers, depot, departed carrier, access, pad, surface, station distance, then no usable trade prices. Age uses the existing `market_updated_at` index with COUNT, retaining the fresh-row join filter.
- Supply only filters exports. Markets with imports remain eligible; a market with neither imports nor eligible exports gets `no_trade_prices`, not a misleading supply exclusion.
- UI shows only nonzero reasons using actual query age/Ls/pad/supply values; older payloads without counts still render.
- Route behavior suite: 12 tests passed (0.022s), including Pergamon Workshop at 1279.7 Ls versus the 1000 Ls cutoff, the exact boundary, reasons, overlap and supply. Node status-label checks: 3 passed; JavaScript syntax check passed.
- Full suite: 1231 tests in 0.859s, passed (1 skipped); exceeds 0.7386s budget. Required timing report passed in 0.787s after permitting its local HTTP fixture socket; largest case was hub status (0.011s), route API case 0.007s. Timing budget remains unmet. No live state-mutating checks.

## Follow-ups

- Coordinator should regenerate the shared iteration archive on integration and assess full-suite timing on the integrated branch.
