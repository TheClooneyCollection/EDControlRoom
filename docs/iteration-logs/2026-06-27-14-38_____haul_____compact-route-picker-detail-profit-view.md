# Iteration Log

- Area: `haul`
- Title: `compact-route-picker-detail-profit-view`
- Started: `2026-06-27 14:38`

## Summary

- Compacted the selected-route detail block inside the `HAUL ROUTES` picker so all key haul parameters stay visible in one screenful.

## Changes

- Reworked the picker detail rendering to keep the search timestamp on the header line and collapse route, cargo, and profit fields into shorter rows.
- Added explicit `Per trip` and `Per hour` labels so both profit figures are always visible for the highlighted route.
- Added focused rendering coverage and re-ran the full suite; the first pass landed at `0.330s`, the required timing report showed existing heavy tests, and the warm-cache rerun finished at `0.293s`.

## Follow-ups

- Live-check the picker against real long commodity names and large tmux/font-size combinations to confirm the compact rows still hold up without awkward wrapping.
