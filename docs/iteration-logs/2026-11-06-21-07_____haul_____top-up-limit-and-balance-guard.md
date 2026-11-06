# Iteration Log

- Area: `haul`
- Title: `top-up-limit-and-balance-guard`
- Started: `2026-11-06 21:07`

## Summary

- The user asked for a configurable top-up limit (default 3) and asked that a credit-limited buy never time out and abort.

## Changes

- New `controls.market.buy_top_up_max_attempts` (default `3` in `defaults/controls.toml`, `>= 0`, `0` disables top-up). It is passed through `HaulMarketSettings` for two-way and multi-leg haul. Log lines now show `(top-up n/N)`.
- `_read_buy_quantity_limit` also caps by `Status.json` `Balance // BuyPrice` when both values are usable. A missing, blank or corrupt `Status.json`, or a balance or price that is invalid, counts as unknown.
- A known zero `MAX` limit backs out to the station menu without waiting for a `MarketBuy` that never comes.
- Before each top-up, both haul loops re-read the balance and the price. If the balance cannot cover one unit, they skip the top-up with a warning and continue.
- The user's local `config.toml`, which is not tracked, now uses `0-99t` flat `3.0s` and `100t+` flat `4.5s`. The running `lan` server needs a restart to pick it up; the user decides when.

## Follow-ups

- `Status.json` freshness is not checked. A valid but outdated balance is trusted.
- A zero limit caused by station stock `0` now warns and continues instead of timing out. In two-way haul, the ship could then fly a leg empty. Revisit if that shows up live.
