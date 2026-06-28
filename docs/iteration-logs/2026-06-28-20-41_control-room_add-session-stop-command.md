# Iteration Log

- Area: `control-room`
- Title: `add-session-stop-command`
- Started: `2026-06-28 20:41`

## Summary

- Added a dedicated `stop` command for persisted haul sessions so operators can freeze session time/profit without clearing totals.

## Changes

- Added persisted session-active/session-elapsed state so a stopped session can keep its frozen duration across saves and remote snapshots instead of resuming wall-clock growth on the next launch.
- Added `stop` command help/dispatch plus persistence plumbing that refuses to stop while a haul is actively running, freezes the current session totals, and resumes from those totals on the next haul without counting the stopped downtime.
- Extended haul/session tests and verified the full suite still passes after the new command and snapshot fields.

## Follow-ups

- Live-check whether operators want the frozen-session state called out explicitly in the haul-panel status line, or whether the current no-ticking time display is clear enough on its own.
