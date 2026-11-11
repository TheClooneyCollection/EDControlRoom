# Iteration Log

- Area: `control-room`
- Title: `docked-sidebar-and-activity-bar`
- Started: `2026-11-11 11:35`

## Summary

- On desktop widths the web sidebar now sticks to the viewport, so its status foot and Hub chip stay at the bottom of the screen while the main content scrolls.
- The activity log on `/haul` and `/controls` is a bar docked to the bottom of the main column. It starts collapsed to one line (title, entry count, newest entry), and a click expands the full scrollable list. The choice is kept per browser.
- Phones (760px and narrower) keep the old layout: sidebar as a nav row, activity panel in the page flow and always expanded.

## Changes

- `web/haul-ui.css`: `.sidebar` is `position: sticky; top: 0; height: 100vh; overflow-y: auto` (phone resets `height: auto`). New `--sidebar-width` token shared by the grid and the dock. New activity toggle and dock rules. Docking only applies under `@media (min-width: 761px)` with `body.has-activity-dock`. `main` pads by `--activity-dock-height` and the connection banner sits above the bar.
- `web/activity-dock.js` (new, served from `/assets/`): toggles `aria-expanded` and `.expanded`, stores `edcr.activityDock.expanded` in localStorage inside try/catch, and mirrors the newest `.activity-row` into the collapsed line through a `MutationObserver`. That way neither `haul-ui.js` nor `controls.js` changed. A `ResizeObserver` publishes the bar height. On phones the toggle is disabled and the list stays shown.
- `web/haul-v1.html`, `web/controls.html`: the activity panel head is now a `<button id="activity-toggle">` with the latest-entry line and a chevron. Both pages load `activity-dock.js`.
- Tests: markup, storage and CSS hooks in `tests/test_control_room_haul_web.py`, and the asset is served in `tests/test_control_room_server.py`.

## Verification

- Checked by eye with headless Chrome over CDP against `control_room.py serve` at 1400x850 and 390x844. Collapsed and expanded bars sit over the main column only. The sidebar foot sits at the viewport bottom. The expanded state survives a reload. The phone layout is unchanged.
