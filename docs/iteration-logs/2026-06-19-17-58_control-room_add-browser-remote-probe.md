# Iteration Log

- Area: `control-room`
- Title: `add-browser-remote-probe`
- Started: `2026-06-19 17:58`

## Summary

- Added a no-build browser probe for the remote observer server so the new CORS/schema/discovery work can be exercised from a real browser before a dedicated web client exists.

## Changes

- Added `tools/scratch/control_room_remote_browser.html`, a standalone HTML/JS page that fetches `health`, `capabilities`, `snapshot`, and the served schema, then opens `WS /session` and can claim operator or request snapshots.
- Updated the scratch-tool README and remote operator runbook so the browser probe is part of the supported validation path for future web-client work.
- Refreshed the Control Room status handoff to call out both CLI and browser smoke probes for remote validation.

## Follow-ups

- If a dedicated web client is started, use the browser probe as the minimal contract check first, then replace its ad hoc rendering with a proper app without changing the server discovery/session surface casually.
