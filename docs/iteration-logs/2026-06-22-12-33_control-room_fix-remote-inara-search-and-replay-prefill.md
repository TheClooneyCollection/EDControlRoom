# Iteration Log

- Area: `control-room`
- Title: `fix-remote-inara-search-and-replay-prefill`
- Started: `2026-06-22 12:33`

## Summary

- Fixed the remote `control_room connect` path so server-started prompt/replay edits repopulate the client command bar and Inara trade-route results render in the shared `TRADE ROUTES` panel instead of staying server-local.

## Changes

- Added command-input prefill state to the shared prompt snapshot, wired prompt/replay helpers to maintain it, and taught the observer client to restore that value/placeholder only when the server explicitly owns the command bar.
- Added trade-route results to the shared control-room snapshot, updated snapshot serialization/deserialization, and rehydrated remote route cards into the observer app so `haul search` and `haul route <n>` work in client/server mode.
- Added regression coverage for server-side snapshot serialization, remote replay-edit prefill, and remote trade-route snapshot application.

## Follow-ups

- Live-test `haul search`, `haul route <n>`, and replay edit in a real `serve` plus `connect` session to confirm the route-card parser and prompt UX hold up under live Inara responses.
