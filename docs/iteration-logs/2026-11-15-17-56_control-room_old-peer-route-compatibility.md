# Iteration Log

- Area: `control-room`
- Title: `old-peer-route-compatibility`
- Started: `2026-11-15 17:56`

## Summary

- Keep older peers usable for hub global searches and searches with an explicit system.

## Changes

- Missing `current_system` now causes 409 only for near searches without an explicit system. Global/explicit-system queries use an empty current-system fallback, never the hub system. Published ship/cargo-capacity state remains required.
- Offline 502 details use the registry node name and the relay wording `not linked to the hub`; the `node` field remains the ID. Unknown IDs use the ID as their display name.
- Behavioral coverage checks old-style global 200, near 409, explicit-system near 200, missing ship/hold, and named offline/unknown responses.
- Full suite: 1233 tests in 0.798 s, OK (1 skipped). Required timing report run because the 0.7398 s budget is exceeded; timing remains an explicit integration open point.

## Follow-ups

- No live check; upgrade peer state publication for near searches using the current location. No changes to server-local search defaults or route-query interfaces.
