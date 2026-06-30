# Iteration Log

- Area: `control-room`
- Title: `market-scrollbar-fix`
- Started: `2026-06-30 12:59`

## Summary

- Fixed the Control Room market panel so overflowing commodity lists show a real visible scrollbar again under Textual `8.2.7`.

## Changes

- Replaced the `#market` widget from a plain `Static` with a `VerticalScroll` container and moved the rendered market markup into an inner `#market-content` `Static`.
- Tightened the regression test to wait for a layout tick and assert `show_vertical_scrollbar` instead of only checking that the widget had scrollable overflow.
- Updated `docs/status/control-room.md` so the handoff notes the current Textual-specific scrollbar fix accurately.

## Follow-ups

- The full suite still exceeds the repo timing budget because Textual app tests dominate runtime; this fix adds one `pilot.pause()` to verify layout-driven scrollbar visibility and that test is now the slowest case in `tools/report_test_timing.py`.
