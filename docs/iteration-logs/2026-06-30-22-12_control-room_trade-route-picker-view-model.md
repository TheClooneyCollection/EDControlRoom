# Iteration Log

- Area: `control-room`
- Title: `trade-route-picker-view-model`
- Started: `2026-06-30 22:12`

## Summary

- Added a trade-route picker ViewModel so the picker display state is translated before Textual widget updates.

## Changes

- Added `TradeRoutePickerViewModel` and `trade_route_picker_view_model()`.
- Rewired `ControlRoomApp._refresh_trade_route_picker()` to consume the picker ViewModel.
- Added ViewModel tests for selected/default/empty route states.

## Follow-ups

- Continue extracting action seams for trade-route picker movement/load/destination commands.
