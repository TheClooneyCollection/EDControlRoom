# Iteration Log

- Area: `control-room`
- Title: `dest-home-alias`
- Started: `2026-07-03 10:28`

## Summary

- Fixed `dest home` so it resolves to the saved `control_room.home_system` before the galaxy-map route prompt/routine sees the destination.

## Changes

- Added home-alias resolution to the destination command parser while preserving the raw command as `dest home` for prompt/history context.
- Reused the existing home-not-set guidance when `dest home` is submitted without a saved home system, preventing a literal route attempt to `home`.
- Added Control Room regressions for saved and missing home-system `dest home` cases, and updated command help, operator docs, and the Control Room status handoff.

## Follow-ups

- Live-check `dest home` after `home set` in the real TUI to confirm the NavRoute mismatch shown in the failed run no longer appears.
