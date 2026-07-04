# Iteration Log

- Area: `haul`
- Title: `recover-wrong-buy-cargo`
- Started: `2026-07-04 17:08`

## Summary

- Added wrong-cargo recovery to two-way haul buy phases: if a buy lands on the wrong commodity, the routine sells the wrong cargo and retries once, then aborts with logging and TTS on the second wrong buy.

## Changes

- Made `market_buy` return immediately when a `MarketBuy` journal event reports a different commodity than the requested target, preserving the wrong commodity in result details.
- Added haul buy-phase recovery that checks Cargo.json after buy, sells unintended cargo with `market_sell`, and retries the intended buy after the first mistake.
- Added `haul_wrong_cargo_aborted` TTS copy and emits it when wrong cargo is bought twice in one haul run.
- Added market and two-way haul regression tests for wrong-item detection, single recovery, and second-mistake abort.

## Follow-ups

- Live-validate the recovery with a small hold before trusting it during high-volume hauling, because the sell step depends on Cargo.json and market sell-list ordering matching live UI behavior.
