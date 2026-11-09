# Iteration Log

- Area: `haul`
- Title: `pass-market-nav-delay`
- Started: `2026-11-09 12:25`

## Summary

- Deck hauls kept buying the commodity 1 to 3 rows above Silver (row 36 at Voltaire Terminal) after `[controls.market] nav_delay_seconds = 0.2`. The 12:17 buy took 7.3s for 36 presses, the same pace as before, because two-way and multi-leg haul never passed `nav_delay_s` and `market_buy`/`market_sell` fell back to their 0.1s default. Only manual `buy`/`sell` read the config.

## Changes

- `HaulMarketSettings` gains `nav_delay_s`, built from `controls.market_nav_delay_seconds`, and every haul market buy/sell call (two-way sell, buy, sell-all recovery; multi-leg sell, buy) passes it.
- Test: `test_market_trades_use_the_configured_nav_delay`.

## Follow-ups

- Deploy to the Deck and watch whether Voltaire Silver buys stop landing short at 0.2s.
- `market_buy`/`market_sell` still default `nav_delay_s=0.1`; making it required would stop a caller silently skipping config, but needs the routine tests updated.
