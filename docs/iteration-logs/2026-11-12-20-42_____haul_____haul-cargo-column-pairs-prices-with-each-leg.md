# Iteration Log

- Area: `haul`
- Title: `haul-cargo-column-pairs-prices-with-each-leg`
- Started: `2026-11-12 20:42`

## Summary

- The `/haul` station lines `Buy … / Sell …` and `Sup … / Dem …` each mixed two commodities (the station's own cargo and the other station's), so `Buy 3,495 / Sell 20,375` read like one item's spread. The Cargo column now shows each leg with its own numbers.

## Changes

- Cargo cell: per leg, `Commodity buy → sell (+margin/t)` then `Sup … · Dem …`. Outbound uses `from_buy_price` → `to_sell_price`, `from_supply` / `to_demand`; return uses `to_buy_price` → `from_sell_price`, `to_supply` / `from_demand`.
- Station columns keep only name, system / Ls and manual landing.
- Routes saved before prices existed show the commodity and `Sup · Dem` only. A leg with no commodity is left out; no commodity at all shows `No buy commodity`.
- A route shown on `/haul` after a hydrate is the node's saved copy: one saved before `daacf4f` has null prices until it is selected again (re-opened from `/routes` or `/markets`).

## Follow-ups

- Full suite runs about 0.79s for 1171 tests, still over the 0.70s budget as before.
