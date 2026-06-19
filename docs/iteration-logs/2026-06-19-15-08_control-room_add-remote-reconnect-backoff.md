# Iteration Log

- Area: `control-room`
- Title: `add-remote-reconnect-backoff`
- Started: `2026-06-19 15:08`

## Summary

- Added automatic remote observer reconnect with exponential backoff so transient ping timeouts or server restarts do not leave the client permanently detached.

## Changes

- Wrapped the remote observer WebSocket session in a reconnect loop with exponential delays from 1 second up to a 30 second cap.
- On reconnect, the client requests a fresh remote snapshot and logs `Observer connection restored.` so stale routine or operator state can self-heal.
- Added client tests for backoff growth/capping and the reconnect messaging/snapshot refresh path.

## Follow-ups

- Live-test server stop/start and forced ping-timeout cases to tune the operator-facing reconnect messaging and confirm retry pacing feels reasonable on LAN.
