# Iteration Log

- Area: `haul`
- Title: `market-buy-top-up`
- Started: `2026-11-06 20:59`

## Summary

- A short market buy used to leave with a partial load. Two-way and multi-leg haul now top up the remainder, up to 2 times, then warn and continue. This makes an undershoot cheap, which unblocks a shorter buy-hold curve.

## Changes

- `market_buy` success details now carry `expected_count`. For `MAX` this is `min(free, stock)`; for a numeric amount it is the requested amount.
- `haul_support.buy_shortfall` compares `expected_count` with `MarketBuy.Count` and returns `None` when either is unknown, so an unknown result never triggers a top-up.
- `haul_two_way._run_market_buy` tops up with `MAX`. `haul_multi_leg._run_buy` tops up the numeric remainder. A failed top-up dispatch is returned. A top-up that buys the wrong commodity uses the existing recovery path. Haul stats already count every `MarketBuy` before departure.
- User-confirmed facts:
  - Holding `UI_Right` past max clamps at max.
  - A second buy's max is the remainder.
  - Top-ups are OK.
  - A manual hold to max at 1137t takes about 3s; the default curve gives 9.1s.

## Follow-ups

- Proposed retune, awaiting user approval: `100t+` flat `4.5s` (keep `0-99t` at `3.0s`, cap `20s`). If no top-ups fire on large buys, try a flat `3.5s` for every size.
- Edge cases:
  - If credits limit the buy, a top-up of 0 affordable units would time out and abort the haul.
  - If `Cargo.json` is stale after the first buy, the top-up `expected_count` is overstated. That wastes a second top-up, but the game clamps the quantity.
- Optional learning of the hold per bucket (step D), only on the user's request.
