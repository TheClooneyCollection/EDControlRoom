# Iteration Log

- Area: `control-room`
- Title: `add-route-picker-dest-shortcut`
- Started: `2026-06-28 20:45`

## Summary

- Added a route-picker keyboard shortcut so operators can send the highlighted haul result's origin system to `dest` without manually copying the system name.

## Changes

- Added `d` handling in the haul route picker to close the modal and dispatch `dest <from_system>` for the currently highlighted Inara route result.
- Updated the route-picker help text and haul command help so the new shortcut is visible in the live UI and the built-in command reference.
- Added protocol/render harness coverage for the `d` shortcut alongside the existing Enter/Esc picker behavior.

## Follow-ups

- Live-check whether operators also want a direct shortcut for the destination-side system, or whether origin-system targeting covers the useful case.
