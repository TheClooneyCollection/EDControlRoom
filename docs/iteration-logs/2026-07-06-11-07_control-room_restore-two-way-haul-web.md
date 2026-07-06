# Iteration Log

- Area: `control-room`
- Title: `restore-two-way-haul-web`
- Started: `2026-07-06 11:07`

## Summary

- Restored the existing `/haul` two-way web page after the Spansh planner work had incorrectly changed its visible UI.

## Changes

- Reverted `web/haul-v1.html` and `web/haul-ui.js` back to the pre-redesign two-way route table/search surface while preserving the shared asset setup.
- Added separate `web/multi-haul.html` and `web/multi-haul.js` for the Spansh-style multi-leg planner and dedicated `command.dispatch_multi_leg_haul` preview path.
- Updated the observer server so `/multi-haul` serves the separate page and `/assets/multi-haul.js` is available without changing `/haul`.
- Moved web tests so two-way assertions cover the original route table surface and Spansh/multi-leg assertions cover the separate multi page.

## Follow-ups

- `/multi-haul` remains UI-only until backend multi-leg route calculation/dispatch support is implemented.
