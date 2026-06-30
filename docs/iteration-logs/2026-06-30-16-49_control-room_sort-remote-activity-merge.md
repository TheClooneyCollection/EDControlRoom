# Iteration Log

- Area: `control-room`
- Title: `sort-remote-activity-merge`
- Started: `2026-06-30 16:49`

## Summary

- Fixed observer activity-log refresh ordering so retained local prompt lines are merged back into remote snapshots by timestamp instead of being appended after newer remote routine output.

## Changes

- Sorted `ObserverControlRoomApp._replace_activity_log()` merges by parsed `ActivityLogEntry.timestamp` before trimming and repainting the widget.
- Added a regression that reproduces the `dest sol` prompt/routine mix, proving `Command`, `Destination`, and settle-prompt lines stay ahead of later `Executing...` and destination routine logs after refresh.

## Follow-ups

- Re-run a live `serve` + `connect` `dest sol` session and confirm repeated snapshot refreshes no longer push retained local prompt lines below newer remote routine output.
