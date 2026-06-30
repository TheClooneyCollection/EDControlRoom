# Iteration Log

- Area: `control-room`
- Title: `connect-command-bar-state`
- Started: `2026-06-30 19:22`

## Summary

- Encapsulated connect-mode command-bar draft/cursor/prefill state.

## Changes

- Added `ObserverCommandBarState` to own command input value, cursor position, and prompt prefill signature.
- Routed command input capture and clear paths through the new state object.
- Kept compatibility properties for existing tests/call sites while centralizing command-bar state.

## Follow-ups

- Move command-bar refresh/restore behavior behind a dedicated view action after replay and trade-route picker state are similarly isolated.
