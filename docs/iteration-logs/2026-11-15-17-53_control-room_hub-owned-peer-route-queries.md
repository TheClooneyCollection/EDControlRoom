# Iteration Log

- Area: `control-room`
- Title: `hub-owned-peer-route-queries`
- Started: `2026-11-15 17:53`

## Summary

- Hub pages query the hub market store directly for a selected peer, removing the hub → peer → hub route-query round trip.

## Changes

- Removed EDDN routes from `NODE_READS`; authenticated hub endpoint uses published peer `current_system`, cargo capacity and ship ID. It never falls back to hub ship/system. Missing/old state returns 409 with update/reconnect guidance; offline/unknown nodes return 502. Known empty ship fields remain empty/zero, matching local query semantics.
- User-confirmed defaults rule: each page uses the server serving it. Hub pages use hub `haul_search.toml` even with a peer selected; peer-local pages resolve their own defaults before asking the hub. No peer search defaults are published. Resolved peer requests no longer inherit hub defaults for any remaining empty fields.
- Ship laden range is already published, but Routes intentionally keeps its existing blank-range fallback to the serving server's haul-search range. Ship state has no pad-size field, so no new inference was added.
- Peer-local EDDN searches use `search_timeout_s`; other hub requests retain their existing timeout.
- Behavior tests cover peer system/hold/ship identity, hub defaults, explicit overrides, authentication, no relay, missing/old/offline state and peer defaults isolation.
- Full suite: 1233 tests in 0.800 s, OK (1 skipped); exceeds 0.7398 s budget. Required timing report run; leading hotspots were existing HTTP/status/journal tests, not the new route tests.

## Follow-ups

- No live hub/peer restart or browser check performed. Existing peers need the new system publication before the hub can answer their routes.
- Other `NODE_READS` are not equivalent: route comparison reads node journal/navroute and caches to its broker; route-compare config is node configuration; Spansh caches a route on that node for later execution; journal-ledger reads node-local journals. Left unchanged.
- Direct hub HTTP queries no longer have a relay deadline. Peer-local searches still depend on the configured search timeout; queries longer than that and external HTTP proxy/client deadlines remain possible. Timing optimization outside this slice is left to integration.
