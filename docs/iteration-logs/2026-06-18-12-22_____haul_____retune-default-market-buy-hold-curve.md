# Iteration Log

- Area: `haul`
- Title: `retune-default-market-buy-hold-curve`
- Started: `2026-06-18 12:22`

## Summary

- Retuned the shipped market buy `MAX` defaults around longer stable holds for small and mid-size cargo loads.
- Raised the default buy-hold cap to `20.0s` and re-fit the `301t+` log segment to start at `5.0s` around `301t` and reach about `8.0s` at `800t`.

## Changes

- Updated the default config loader, routine fallback defaults, example config, and operator market-timing doc to use the new hold curve.
- Updated routine and config tests to assert the new shipped defaults and progress output.

## Follow-ups

- Live-validate the new `301t+` curve in Odyssey/CrossOver to confirm the longer default dwell no longer undershoots large buys.
-

## Changes

-

## Follow-ups

-
