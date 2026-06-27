# Iteration Log

- Area: `control-room`
- Title: `trace-route-picker-modal-profit-path`
- Started: `2026-06-27 15:37`

## Summary

- Added dedicated route-picker tracing so live Control Room runs can show whether trip/hour profit disappears at load time, label formatting time, or detail-markup time.

## Changes

- Added a separate `artifacts/control-room-debug.log` JSONL trace sink for Control Room UI diagnostics instead of mixing modal debug lines into the existing artifact event mirror.
- Instrumented `_set_trade_routes_loaded`, `_refresh_trade_route_picker`, and `_update_trade_route_detail` to log the first route’s trip/hour profit plus the exact modal list label and detail markup being rendered.
- Added a Control Room test for the debug artifact writer and re-ran the full unittest suite successfully in `0.241s`.

## Follow-ups

- Re-run `uv run control_room.py`, perform `haul search`, and inspect `artifacts/control-room-debug.log` to see where the route-picker modal still loses the profit fields in the live app path.
