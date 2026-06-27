# Iteration Log

- Area: `control-room`
- Title: `move-haul-search-results-into-picker`
- Started: `2026-06-27 14:29`

## Summary

- Replaced the always-on haul search route list with a dedicated `HAUL ROUTES` picker so route results behave like a modal selection flow instead of occupying the right-side panel.

## Changes

- Added local picker state plus picker widgets in `ControlRoomApp`, with `Up`/`Down` selection, `Enter` to dispatch `haul route <n>`, and `Esc`/`q` to dismiss.
- Changed the `TRADE ROUTES` panel rendering to a compact search summary/status block while the full route list and per-route detail moved into the picker.
- Auto-opened the picker when a haul search completes successfully in local mode and when a remote snapshot delivers a newly completed route search.
- Updated unit coverage for the new picker flow and kept the full `uv run python3 -m unittest discover -s tests` suite passing in `0.280s`.

## Follow-ups

- Live-check the picker in both embedded and `control_room connect` sessions to confirm the modal handoff feels right under real Inara latency and routine-heavy sessions.
