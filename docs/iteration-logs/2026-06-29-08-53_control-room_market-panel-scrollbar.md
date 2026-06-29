# Iteration Log

- Area: `control-room`
- Title: `market-panel-scrollbar`
- Started: `2026-06-29 08:53`

## Summary

- Added vertical overflow scrolling to the Control Room market panel so long station commodity lists expose a scrollbar instead of clipping in place.

## Changes

- Set `#market` to `overflow-y: auto` in the Textual app CSS so the existing market widget can scroll when content exceeds panel height.
- Added a mounted-app regression test that renders an oversized remote market snapshot and asserts the market panel both enables vertical scrolling and reports overflow.
- Rechecked the focused control-room test file and the full unittest suite; both passed.

## Follow-ups

- Live-check the market panel in a real terminal session to confirm the scrollbar feel is acceptable alongside the existing activity-log and haul-panel layout.
