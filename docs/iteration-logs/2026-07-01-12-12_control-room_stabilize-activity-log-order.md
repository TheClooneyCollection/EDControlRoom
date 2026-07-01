# Iteration Log

- Area: `control-room`
- Title: `stabilize-activity-log-order`
- Started: `2026-07-01 12:12`

## Summary

- Stabilized activity log ordering when connect mode mixes client-local prompt logs with server routine logs.

## Changes

- Added app-local first-observed display ordering for activity entries.
- Changed activity redraws to preserve display order instead of re-sorting merged local/remote logs by wall-clock timestamp.
- Added a regression covering server entries with earlier timestamps arriving after local prompt transcript entries.

## Follow-ups

- Live-check `dest` and `haul route` prompt/routine transcripts in connect mode against a remote server.
