# Iteration Log

- Area: `control-room`
- Title: `remove-backend-current-snapshot`
- Started: `2026-06-30 21:44`

## Summary

- Removed the backend `current_snapshot()` contract so local and remote apps cannot rebuild UI from backend-owned snapshots.

## Changes

- Dropped cached snapshot seeding from `RemoteObserverBackend`.
- Updated connect/client tests to assert hydrated data-source state and backend events instead of snapshot compatibility.
- Kept `publish_snapshot()` as a no-op/external-sink compatibility hook pending server/protocol cleanup.

## Follow-ups

- Remove the remaining server broker/protocol snapshot compatibility path.
