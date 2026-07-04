# Iteration Log

- Area: `web`
- Title: `routine-credit-summary`
- Started: `2026-07-04 18:32`

## Summary

- Web Haul active routine credits now show the current run and accumulated total together.

## Changes

- Renamed the active routine metric label from `Current run` to `Current / Accumulated`.
- Rendered the metric value as `current_run_profit / accumulated_profit` using the existing credit formatter for both sides.
- Added static web coverage for the label and combined formatter expression.

## Follow-ups

- Confirm on-device readability once live profit values grow into multi-million or billion credit ranges.
