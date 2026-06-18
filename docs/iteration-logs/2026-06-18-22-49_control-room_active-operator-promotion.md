# Iteration Log

- Area: `control-room`
- Title: `active-operator-promotion`
- Started: `2026-06-18 22:49`

## Summary

- Implemented the first active-operator promotion policy: the first authenticated client becomes the operator automatically, later authenticated clients can claim the role explicitly, and role-aware snapshots now track that assignment end to end.

## Changes

- Updated the observer-session broker to auto-promote the first authenticated client, allow explicit operator claims, and fail over to the next connected client when the current operator disconnects.
- Extended the session protocol with `command.request_active_operator`, updated `connection_ready` and snapshot payloads to reflect the broker-assigned role, and exposed `--claim-operator` on `control_room connect`.
- Added regression coverage for auto-promotion, explicit claim, and role-aware snapshot payloads, then re-ran compile checks and the full unittest suite.

## Follow-ups

- The main remaining work is live validation and broader routine/prompt coverage through the headless host now that role assignment, command transport, and simple command execution are all in place.
