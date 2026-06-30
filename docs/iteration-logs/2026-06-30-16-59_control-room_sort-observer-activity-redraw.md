# Iteration Log

- Area: `control-room`
- Title: `sort-observer-activity-redraw`
- Started: `2026-06-30 16:59`

## Summary

- Fixed observer activity redraw ordering so preserved local prompt lines are merged back into remote snapshots chronologically instead of always appearing below newer remote routine lines.

## Changes

- Reintroduced timestamp sorting inside `ObserverControlRoomApp._replace_activity_log()` so merged remote plus local activity is ordered by `ActivityLogEntry.timestamp` before repaint.
- Added a regression covering the exact `dest sol` plus remote cancel case: local `:34` prompt lines now render above remote `:35` and `:38` routine/cancel lines after snapshot refresh.

## Follow-ups

- Re-run a live `serve` + `connect` `dest sol` flow and confirm the activity panel keeps `Command`, `Destination`, and settle-prompt lines above later `Executing...` / cancellation lines during reconnects or periodic snapshot refreshes.
