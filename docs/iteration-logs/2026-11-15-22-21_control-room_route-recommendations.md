# Iteration Log

- Area: `control-room`
- Title: `route-recommendations`
- Started: `2026-11-15 22:21`

## Summary

- Built approved plan 0019: EDDN-only haul search and explicit, voiced route recommendations for local games and peers.

## Changes

- Eight ordered commits cover search, pure ranking, config, node state/TTS, changed-data checks, peers, Better routes UI and docs. Independent core/config and web slices were built in separate worktrees, integrated linearly and their agents/worktrees closed.
- Approved deviation: `/haul` opts into server-side viewed-ship laden range with `ship_range=1`; explicit range wins and missing ship retains fallback. `/routes` default unchanged. Search never selects the first result automatically.
- Thresholds require both +15% and +20m Cr/h; 300 s checks and TTS gap; top 10 from 200; current-price selected baseline with missing-input reasons; node-owned dismissals; no automatic selection, travel or haul start.
- Hub computes from each connected node's ship and selected route, delivers a new link frame, and peers use normal hydrate/TTS/mute. Disconnected pages retain last results with disabled actions and check time.
- Full integration suite: `uv run python3 -m unittest discover -s tests`, 1271 tests in 0.946 s, OK (1 skipped). Worktree used the existing uv project environment with `--no-sync`; existing HTTP fixture needs localhost permission. Timing report 1271 / 1.016 s, above 0.7626 s budget already exceeded before this work; Node flow ~68 ms and existing four transit tests ~34–36 ms each lead. No unrelated optimization.
- Plain function/DOM/API/socket fakes cover search/select/copy/retry, thresholds, change gating, stale-query suppression, two peers, frame-to-hydrate/TTS, disconnect retention and server Select/Dismiss roundtrips. Mocked Chromium 1440/390 px `/haul?node=forge` has no script errors or horizontal overflow; mobile screenshot reviewed.
- Real local market store read-only timing: 100 Ly 4.531 s, 250 Ly 18.271 s, 1895 eligible markets / 200 results (720 t, 31.5 Ly fixture inputs); retain 100 Ly. No game input, real route selection or live start sent.

## Follow-ups

- Secondary owns integration/deployment. Live-check hub and forge after restart: EDDN rows, explicit select/copy/travel/start, one recommendation within the check window, TTS gap/mute/disabled message, dismiss and offline retention.
- During a running forge haul confirm recommendation does not change selected/running route and Start remains refused. Look-only browser checks must use `/haul` without a `#route=` fragment.
- Suite timing budget remains unmet; inspect existing transit sleeps and Node process startup separately if optimization is requested.
