# Iteration Log

- Area: `web`
- Title: `allow-all-connected-operators`
- Started: `2026-07-04 17:03`

## Summary

- Opened the remote/web operator policy so every authenticated connected client is treated as an operator instead of competing for a single active-operator slot.

## Changes

- Changed the observer session broker to register connected clients as `active_operator` and resolve all live sessions to that role.
- Removed server-side read-only role gates from websocket command handlers; command validation, auth, and transport-availability checks still apply.
- Updated `/haul` to avoid self-demotion on `event.active_operator_changed` and replaced old active-operator-required copy with connection-oriented wording.
- Updated server and web tests for the new all-connected-operators policy.

## Follow-ups

- Live-check two simultaneous `/haul` browser clients against one `serve` process to confirm both can search/start/stop without role churn.
