# Iteration Log

- Area: `control-room`
- Title: `decouple-view-actions`
- Started: `2026-07-01 10:13`

## Summary

- Decoupled the current market and trade-route picker ViewActions from `ControlRoomApp`/Textual display mechanics.

## Changes

- Updated plan 0008 so ViewActions are explicitly UI-neutral intent dispatchers backed by injected dependencies.
- Replaced app-coupled market/trade-route action implementations with pure ViewAction classes and dependency protocols.
- Added `app_view_actions.py` as the current Textual/ControlRoomApp adapter for logging, refresh, command dispatch, and focus behavior.
- Reworked ViewAction tests to use dependency fakes instead of app/widget stubs.

## Follow-ups

- Continue moving prompt/replay/command-bar interactions behind the same display-neutral action dependency pattern.
