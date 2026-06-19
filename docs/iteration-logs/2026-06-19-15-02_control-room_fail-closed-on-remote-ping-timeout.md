# Iteration Log

- Area: `control-room`
- Title: `fail-closed-on-remote-ping-timeout`
- Started: `2026-06-19 15:02`

## Summary

- Made remote observer clients fail closed after an established session drops so stale remote routine state does not linger after ping timeouts or other WebSocket disconnects.

## Changes

- Added a remote-backend disconnect handler that clears stale active-operator and routine UI state, emits a snapshot refresh, and logs the disconnect reason locally.
- Kept pre-connection command queueing intact for the initial connect/startup window, but reject new commands after a previously connected session has dropped.
- Added client tests covering disconnect-state cleanup and command rejection after disconnect.

## Follow-ups

- Live-test a real ping-timeout or server-stop case to confirm the TUI recovers cleanly and the reconnect workflow remains obvious to the operator.
