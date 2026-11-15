# Iteration Log

- Area: `haul`
- Title: `fold-projected-rate-into-current-run-text`
- Started: `2026-11-15 18:40`

## Summary

- User correction to 8dfc358: the projected rate belongs in the existing `routine-current-run` text, not a separate metric.

## Changes

- `routine-current-run` reads `current / accumulated / projected`, e.g. `50.3m CR / 320.0m CR / ~250.0m/h`; the third part is `-` before the first sale. Same session-based rate (`sessionProfit / session_elapsed_s × 3600`).
- Removed the `Projected` metric and the `session-metrics` grid rule added only for it; the label is now `Current / Accumulated / Projected`.

## Follow-ups

- None.
