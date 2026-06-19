# Iteration Log

- Area: `control-room`
- Title: `add-browser-remote-visibility`
- Started: `2026-06-19 18:10`

## Summary

- Expanded the hosted browser probe from a command surface into a more legible remote operator surface by adding connected-client and recent-activity visibility directly in the page.

## Changes

- Added dedicated browser-probe panels for connected clients and recent activity, derived from the live snapshot and incremental activity-log events.
- Kept those panels refreshed as websocket messages arrive so the browser path surfaces operator-relevant state instead of forcing the user to inspect the raw snapshot JSON alone.
- Updated endpoint coverage plus the remote operator docs/status handoff to reflect that browser validation now covers connected-client and activity visibility too.

## Follow-ups

- If a dedicated web client is built, preserve these basic visibility surfaces early so remote operators do not need a separate raw-state/debug page to understand session state.
