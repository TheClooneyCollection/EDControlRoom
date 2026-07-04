# Iteration Log

- Area: `control-room`
- Title: `market-lock-pins-current-market`
- Started: `2026-07-04 05:13`

## Summary

- Changed Control Room market lock semantics from display freeze to current-market pinning.

## Changes

- Added `MarketData.market_id`, loaded Elite `MarketID` from `Market.json`, and carried it through local data-source copies and hydrate parsing.
- Updated local and remote market presentation sync so locked panels continue rendering matching-market updates while holding back different-market data until unlock.
- Changed operator-facing copy from frozen/locked wording to pinned/following wording and added regressions for local, remote, protocol, and rendering behavior.

## Follow-ups

- Live-check with real `Market.json` updates that Elite emits stable `MarketID` across repeated visits to the same station market.
