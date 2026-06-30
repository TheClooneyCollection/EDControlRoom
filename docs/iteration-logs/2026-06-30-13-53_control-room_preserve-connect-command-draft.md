# Iteration Log

- Area: `control-room`
- Title: `preserve-connect-command-draft`
- Started: `2026-06-30 13:53`

## Summary

- Fixed a `connect`-mode regression where periodic remote snapshot refreshes could wipe the local command-bar draft while the active operator was typing.

## Changes

- Added observer-local command-input draft tracking so steady-state snapshot refreshes no longer clear freeform commands or partially edited local prompt values.
- Seeded the draft only when a prompt prefill actually changes, so new local prompt steps still populate correctly without clobbering later edits.
- Added regression coverage for both plain command typing and local prompt typing during remote snapshot updates.

## Follow-ups

- Live-validate the fix in a real `control_room connect` session to confirm Textual input-change events behave the same as the unit-test harness.
