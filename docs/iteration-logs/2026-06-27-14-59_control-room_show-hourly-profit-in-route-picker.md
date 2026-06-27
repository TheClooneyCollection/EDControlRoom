# Iteration Log

- Area: `control-room`
- Title: `show-hourly-profit-in-route-picker`
- Started: `2026-06-27 14:59`

## Summary

- Added compact per-hour profit prefixes to haul route picker rows and reflowed the selected-route detail into two vertical columns so the picker uses the available width better.

## Changes

- Added a renderer helper that converts Inara `profit_per_hour` strings into the requested `[XX.Ym/h]` list prefix without changing the trade-route snapshot schema.
- Reworked the route-detail markup so `From/To`, `Buy/Return`, `Route/Per unit`, and `Per trip/Per hour` render as paired columns instead of one long stacked block.
- Extended Control Room rendering tests for the new route-row prefix and detail layout, then re-ran `uv run python3 -m unittest discover -s tests` successfully in `0.290s`.

## Follow-ups

- Live-check the picker width in a real Control Room session to decide whether the detail box height should shrink now that the content is denser.
