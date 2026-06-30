# Iteration Log

- Area: `control-room`
- Title: `remove-slow-market-ui-tests`
- Started: `2026-06-30 13:49`

## Summary

- Removed two slow Textual market-panel harness tests after confirming they were exercising widget animation and idle-wait behavior more than repo logic.

## Changes

- Dropped the market-panel scrollbar test that required a full `ControlRoomApp.run_test()` cycle to assert `VerticalScroll` overflow behavior.
- Dropped the market-panel tab-switch test that waited on Textual `Tabs` underline animation before asserting rendered buy/sell content.
- Kept the lower-cost `market_markup(...)` rendering coverage as the remaining check for buy-versus-sell market output.

## Follow-ups

- If market panel regressions need coverage again, prefer state or rendering tests that avoid `pilot.pause()` and widget animation timing.
