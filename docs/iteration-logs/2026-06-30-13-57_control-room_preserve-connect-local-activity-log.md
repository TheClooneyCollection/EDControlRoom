# Iteration Log

- Area: `control-room`
- Title: `preserve-connect-local-activity-log`
- Started: `2026-06-30 13:57`

## Summary

- Fixed a `connect`-mode regression where client-local activity-log output briefly appeared and then got wiped by the next remote snapshot refresh.

## Changes

- Overrode observer activity-log replacement to merge the server snapshot log with retained client-local entries instead of treating the snapshot as the only source of truth.
- Kept observer-local `_log()` writes out of the headless protocol stream while still preserving them in the visible log across later snapshot replacements.
- Added regression coverage showing a local help-style entry surviving a remote snapshot refresh that still contains older server `Unknown command` entries.

## Follow-ups

- Live-validate in a real `control_room connect` session that local prompt/help output remains visible while remote activity continues streaming underneath it.
