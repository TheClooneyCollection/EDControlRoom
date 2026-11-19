# Iteration Log

- Area: `tests`
- Title: `test-timing-m6-wrap-up`
- Started: `2026-11-19 23:17`

## Summary

- M6 test-timing: full suite 1295 tests, `Ran` before 1.173/1.241/1.232 s, after 0.885/0.875/0.910 s. Budget is 0.777 s (0.0006 s/test), so it is still about 0.1 s over.

## Changes

- `test_haul_two_way`: nav-panel tests had an empty `Cargo.json`, skipping the `market_sell` stop stub and hitting the real `market_buy` menu timeout (~1500 Status.json reads each). Fixture now carries cargo; added a `reason == stop after transit` assertion. File 0.224 -> 0.07 s (3 runs each).
- Snapshot/fetch/eddn routes: reuse serialized empty schema bytes, cache immutable galaxy seed, bypass macOS proxy discovery for loopback HTTP. Fetch 0.043 -> 0.025 s, routes 0.019 -> 0.015 s.
- Control Room/server/hub/relay: module-scoped UTC adapter (`tests/fixtures/timezone.py`) avoids per-call OS timezone lookups. Hub 0.108 -> 0.068 s, server 0.13 -> 0.098 s, relay 0.113 -> 0.087 s.
- `test_control_room`: command harness records state writes in memory; persistence tests keep real files. 0.205 -> 0.172 s.
- Investigated, no change: `test_haul_eddn_web` Node flow (0.07 s: ~40 ms Node startup, ~26 ms JS incl. ~10 ms locale init; already one subprocess). Web/hub remaining cost is real ASGI/websocket round trips.

## Follow-ups

- Reaching 0.777 s needs another ~0.1 s: the Node test is a ~0.07 s floor, so either drop coverage, split it onto a slow suite, or revisit the budget (test count grew since the 0.71 s budget was set).
