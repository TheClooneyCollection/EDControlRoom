# Iteration Log

- Area: `web`
- Title: `scroll-haul-activity-history`
- Started: `2026-07-04 16:59`

## Summary

- Fixed the `/haul` Activity panel so hydrated activity history remains available in a scrollable log instead of being capped to the newest eight rows.

## Changes

- Added a bounded `.activity-list` scroll region with keyboard focus and `role="log"` metadata.
- Changed `renderActivityLog()` to render all current activity entries newest-first and show the entry count in the panel status.
- Added static web regression coverage to catch the old `slice(-8)` cap and missing scroll container.

## Follow-ups

- Live-check the panel with a long running `serve` session to confirm the chosen max height is comfortable on the intended browser display.
