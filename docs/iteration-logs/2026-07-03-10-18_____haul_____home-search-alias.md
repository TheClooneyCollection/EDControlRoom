# Iteration Log

- Area: `haul`
- Title: `home-search-alias`
- Started: `2026-07-03 10:18`

## Summary

- Added `haul search home` as an alias for the saved `control_room.home_system`, so operators can reuse the configured home system as the Inara search center.

## Changes

- Resolved the `home` alias inside the haul-search command parser before opening the editable Inara search prompt, while preserving the raw command as `haul search home` for prompt/history context.
- Reported the existing home-not-set guidance when the alias is used without a saved home system instead of treating `home` as a literal system name.
- Updated command help, operator docs, and haul status handoff, and added Control Room regression coverage for saved and missing home-system alias cases.

## Follow-ups

- Live-check one `haul search home` run after `home set` in the real TUI to confirm the prompt prefill and route picker feel correct with live Inara results.
