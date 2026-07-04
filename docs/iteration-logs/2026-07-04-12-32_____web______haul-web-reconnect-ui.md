# Iteration Log

- Area: `web`
- Title: `haul-web-reconnect-ui`
- Started: `2026-07-04 12:32`

## Summary

- Added visible websocket error recovery UI to Haul Web with manual reconnect and capped exponential retry.

## Changes

- Added a persistent connection banner under the `/haul` page header for disconnected, websocket-error, auth-error, and reconnecting states.
- Added topbar and banner reconnect buttons that clear pending retry timers and reconnect immediately.
- Added client-side exponential retry from 1s up to 30s for websocket close/error and disconnected command attempts.
- Changed first-connection failure handling so only explicit server close code `4401` is treated as token rejection.
- Added static web regression coverage for the reconnect UI and retry semantics.

## Follow-ups

- Live-check reconnect behavior against a stopped/restarted `control_room.py serve` process and confirm browser state recovers from hydrate after reconnection.
