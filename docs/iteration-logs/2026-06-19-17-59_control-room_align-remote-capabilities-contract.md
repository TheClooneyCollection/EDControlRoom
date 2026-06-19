# Iteration Log

- Area: `control-room`
- Title: `align-remote-capabilities-contract`
- Started: `2026-06-19 17:59`

## Summary

- Corrected the remaining capability-contract drift so the design note, checked-in schema, and runtime-discovered auth metadata all describe the same remote observer behavior.

## Changes

- Updated the protocol design note to match the real first-connected-client active-operator policy plus explicit operator claiming and disconnect failover.
- Expanded the capabilities payload schema to include the auth metadata and schema URL fields that the server actually returns.
- Added regression coverage so future schema edits have to keep the capabilities contract aligned with the runtime surface.

## Follow-ups

- If the remote surface grows again, update the runtime constants and the checked-in schema together in the same changeset instead of letting the design note drift ahead or behind implementation.
