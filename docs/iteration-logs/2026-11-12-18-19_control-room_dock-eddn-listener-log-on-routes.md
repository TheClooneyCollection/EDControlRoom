# Iteration Log

- Area: `control-room`
- Title: `dock-eddn-listener-log-on-routes`
- Started: `2026-11-12 18:19`

## Summary

- `/routes` EDDN listener panel now uses the shared activity dock: docked to the bottom on desktop widths, collapsed to the newest entry, expandable, phones keep it in flow.

## Changes

- `web/routes.html`: panel takes the `activity-panel` / `activity-toggle` / `activity-latest` / `activity-list` markup and loads `activity-dock.js`; the page-local `.eddn-log` CSS is gone.
- `web/routes.js`: `appendLog` writes `.activity-row` rows (time + text) into `#activity-list`; `activity-dock.js` is unchanged.
- Dock test now covers `routes.html`.

## Follow-ups

- The expanded state shares one localStorage key with the haul, controls and travel pages.
- Not yet checked in a browser.
