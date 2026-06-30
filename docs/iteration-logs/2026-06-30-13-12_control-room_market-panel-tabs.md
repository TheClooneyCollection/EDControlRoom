# Iteration Log

- Area: `control-room`
- Title: `market-panel-tabs`
- Started: `2026-06-30 13:12`

## Summary

- Split the Control Room market panel into native `Buy` and `Sell` tabs without changing any market commands or backend data flow.

## Changes

- Added a tab strip above the existing market scroll view and kept the panel data/render refresh path local to the UI state.
- Updated the market renderer so the active tab shows only its selected trade side while preserving market filtering, sorting, and empty-state messaging.
- Extended Control Room tests to cover sell-side rendering, tab-specific rendering, and live tab switching in the Textual app.

## Follow-ups

- Live-check the tab strip in a real terminal session to confirm mouse/tab navigation feels acceptable for operators; no command-path fallback was added in this slice.
