# Iteration Log

- Area: `control-room`
- Title: `escape-route-picker-profit-prefix`
- Started: `2026-06-27 15:15`

## Summary

- Escaped the haul route picker’s literal `[xx.xm/h]` prefix so markup-aware list rendering can show it instead of swallowing it.

## Changes

- Changed the route-row prefix formatter to emit `[[88.3m/h]]` in source text so the picker renders a literal `[88.3m/h]`.
- Updated the Control Room route-label assertion to match the escaped prefix source form and re-ran the full unittest suite.
- Full suite passed via `uv run python3 -m unittest discover -s tests` in `0.321s`; per repo policy, `tools/report_test_timing.py --top 10 --sort slowest` then reported `suite_status=ok total_seconds=0.327`.

## Follow-ups

- Re-check the live picker after restart; if the prefix still does not appear, inspect the exact running Control Room / serve process because the code and live scraper output now both contain the profit fields.
