# Iteration Log

- Area: `control-room`
- Title: `add-market-view-actions`
- Started: `2026-06-30 18:05`

## Summary

- Added the first view-action surface for local market panel presentation state.

## Changes

- Added `ControlRoomViewActions` and `LocalMarketPanelActions`.
- Wired market tab activation and `market lock` / `market unlock` / `market filter` / clear commands through market view actions.
- Added focused tests for market view actions.

## Follow-ups

- Add view actions for command bar, replay browser, and trade-route picker.
- Continue moving command parsing away from direct app state mutation.
