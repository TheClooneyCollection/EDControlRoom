# Iteration Log

- Area: `control-room`
- Title: `remove-snapshot-message-parser`
- Started: `2026-06-30 18:54`

## Summary

- Removed legacy snapshot parsing/export paths from the remote message parser.

## Changes

- Replaced `protocol/from_message.py` with a minimal parser for current activity and announcement events.
- Removed `snapshot_from_message` from protocol exports.
- Removed the unreachable snapshot-event branch from the remote websocket receive loop.
- Deleted client coverage for parsing `state.snapshot` wire messages.

## Follow-ups

- Continue removing internal/local snapshot compatibility after the remaining connect UI surfaces move to data-source/view-action ownership.
