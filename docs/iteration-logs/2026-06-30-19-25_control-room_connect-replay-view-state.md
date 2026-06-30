# Iteration Log

- Area: `control-room`
- Title: `connect-replay-view-state`
- Started: `2026-06-30 19:25`

## Summary

- Encapsulated connect replay-browser local UI state in a dedicated `ObserverReplayViewState`.

## Changes

- Replaced scattered observer-local replay filter/open/selected-entry fields with one capture/apply object.
- Kept hydrate/snapshot-compat application from overwriting replay-browser local state directly.
- Verified `tests/test_control_room_client.py` and the full unittest suite.

## Follow-ups

- Continue moving trade-route picker and remaining prompt interaction state behind view-action/data-source-owned seams.
