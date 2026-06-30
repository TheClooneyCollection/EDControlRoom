# Iteration Log

- Area: `control-room`
- Title: `fix-remote-activity-timestamps`
- Started: `2026-06-30 16:46`

## Summary

- Fixed observer activity log rendering so remote entries keep their stored protocol timestamps during both snapshot redraws and incremental append events.

## Changes

- Made `build_log_text()` require a valid timestamp and render from that value instead of falling back to the local wall clock.
- Updated embedded and observer Control Room activity writers to render from `ActivityLogEntry.timestamp`, including local entries after creating the protocol log object.
- Added regression coverage for strict timestamp enforcement, remote snapshot redraw preservation, and incremental observer activity append rendering.

## Follow-ups

- Re-run a live `serve` + `connect` `dest sol` flow to confirm prompt lines and delayed execution lines now keep stable ordering under repeated snapshot refreshes.
