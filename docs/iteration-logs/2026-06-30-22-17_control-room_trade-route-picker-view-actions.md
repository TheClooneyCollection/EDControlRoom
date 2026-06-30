# Iteration Log

- Area: `control-room`
- Title: `trade-route-picker-view-actions`
- Started: `2026-06-30 22:17`

## Summary

- Extracted trade-route picker close/move/load/destination behavior into a ViewActions object.

## Changes

- Added `TradeRoutePickerActions` and `LocalTradeRoutePickerActions`.
- Rewired `ControlRoomApp` trade-route helper methods to delegate through `self._view_actions.trade_routes`.
- Added direct ViewAction tests for picker selection movement and command dispatch.

## Follow-ups

- Replay browser actions remain local app methods and are the next candidate for extraction.
