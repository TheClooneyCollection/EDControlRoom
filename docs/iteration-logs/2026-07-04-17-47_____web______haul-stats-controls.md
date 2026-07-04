# Iteration Log

- Area: `web`
- Title: `haul-stats-controls`
- Started: `2026-07-04 17:47`

## Summary

- Added haul stats controls to the web active haul routine panel.

## Changes

- Added `Clear stats` and `Stop stats` buttons below the active routine metrics in `web/haul-v1.html`.
- Wired the buttons through existing websocket `command.submit_input` handling: `new_session` clears persisted haul stats and `stop` freezes persisted haul stats.
- Kept `Stop stats` disabled while a routine is active, matching the existing backend command rule that refuses to stop the stats clock during an active haul.
- Verified phone-width layout at 390px still has no horizontal overflow and the stats controls stack cleanly.

## Follow-ups

- Live-check the stats controls against a served `/haul` session to confirm operator-facing activity messages are clear enough after backend command logs arrive.
