# Iteration Log

- Area: `haul`
- Title: `segmented-market-buy-hold-timing`
- Started: `2026-06-18 07:28`

## Summary

- Replaced the single buy-hold timing formula with ordered configurable buy-hold segments.
- Default buy timing now uses `0-99t` flat `1.0s`, `100-300t` linear, and `301t+` log tapering.

## Changes

- Added `[[controls.market.buy_hold_segments]]` config parsing and validation with per-segment `start`, `function`, and function-specific parameters.
- Updated market, Control Room, two-way haul, and multi-leg haul paths to use the new segmented buy-hold model.
- Rewrote the operator doc and example config to explain segment ordering, `log1p`, and the new default ranges.

## Follow-ups

- Live-validate the default `301t+` log segment against real large-capacity buys to see whether the post-300 drop from the linear segment should be softened.
