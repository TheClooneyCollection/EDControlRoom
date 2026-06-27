# Iteration Log

- Area: `control-room`
- Title: `remove-haul-search-summary-panel`
- Started: `2026-06-27 14:44`

## Summary

- Removed the leftover haul-search summary panel so the `HAUL ROUTES` picker is the only operator-facing search-results surface.

## Changes

- Dropped the `TRADE ROUTES` widget from the main Control Room layout and stopped refreshing the redundant summary markup.
- Removed the old summary renderer and its tests, while keeping the shared `TradeRoutesData` snapshot/model for picker state and remote route hydration.
- Re-ran the full `uv run python3 -m unittest discover -s tests` suite after the UI cleanup.

## Follow-ups

- Live-check the reclaimed right-side space in a real session to decide whether the `MARKET` and `HAUL` panels should be rebalanced now that the extra summary panel is gone.
