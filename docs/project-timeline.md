# Project Timeline

Stages of the project as of v1.38.0 (2026-11-12), from `main` history, git tags and GitHub release titles. Dates are commit dates.

## Headline numbers

- First commit: 2026-05-25, `2e4bd31 chore: a new beginning` (fresh repo; restarted from an older Windows-only autopilot prototype, then ported macOS-first).
- Current version: v1.38.0 (2026-11-12, "Route Prices and Fleet Carriers"). 45 tags, v1.0.0 to v1.38.0.
- Commits: about 884 on main.
- Commits per month: May 44, Jun 430, Jul 113, Aug 0, Sep 31 (docs only), Oct 0, Nov 266 (to the 12th).
- Busiest days: 2026-11-11 (114 commits, 6 releases v1.31 to v1.36), 2026-06-30 (52), 2026-06-07 (51).
- Test suite (`def test_` count): v1.0.0 154, v1.7.3 354, v1.12.0 476, v1.17.0 614, v1.22.0 796, v1.30.0 1047, v1.38.0 1171.
- Versioning is semver-style tags (vX.Y.Z), not date-based.

## Stage 0: macOS port foundation, 2026-05-25 to 2026-06-05

No releases. Diagnostics, native macOS input via Quartz CGEvent, a bindings viewer TUI, then journal-driven routines.

- `75d3903` feat: add diagnostics foundation for config and runtime checks (05-25)
- `29431db` feat: post key events through quartz cgevent on macos (05-26)
- `cbd2a03` feat: add journal watcher and first routine harness (06-05)

## Stage 1: functional TUI, 2026-06-06 to about 2026-06-18

Releases v1.0.0 ("CLI Control Room for Elite Dangerous", 06-07) through v1.11.0 (06-18). The Control Room TUI, haul loop, two-way hauling, queued TTS, Windows input backend and cross-platform validation (v1.5.0, 06-09), haul recovery and docking polish. 11 releases in 4 days (06-07 to 06-10).

- `59aee0d` feat: add control room TUI for live ship status and routine dispatch (06-06)
- `166923a` feat: add haul loop with ProgressShipControls extraction (06-06)
- `75734bd` feat: add windows input backend (06-08)

Nuance: it was "unpolished" but not untested. It shipped v1.0.0 with 154 tests, and the app was split into modules by responsibility on day 2 (`0548afa`, 06-07).

## Stage 2: client/server split, REST + WebSocket, 2026-06-15 to 2026-06-22

Protocol drafted 06-15, groundwork and remote observer client 06-18, v1.12.0 "Control Room Client-Server Split" (06-19), v1.13.0 "Remote Observer Browser Workflow" (06-20). Model: the server runs next to the game, a TUI "observer" client connects remotely, with operator gating and bearer auth.

- `c996cda` docs: draft control room client-server protocol (06-15)
- `4c3f66f` feat: add control room observer client-server groundwork (06-18)
- `48af5e6` test: add websocket remote validation coverage (06-19)

Nuance: the first browser client (a "browser remote probe") already landed in this stage on 06-19 (`b6dab05`), so the web started here, not in stage 3.

## Stage 2.5: backend-driven UI migration, 2026-06-27 to 2026-07-01

v1.14.0 to v1.16.0 added Inara haul search. Then on 06-30 (52 commits) the "Composable Control Room" refactor: panel view models, a server "hydrate" data stream fanned out to all clients, and server snapshots replaced with data refresh, so every client renders from backend data. Released as v1.17.0 "Composable Control Room" (07-01). This is what made the later web UI and hub cheap.

- `e4b33f1` docs: plan composable control room refactor (06-30)
- `2ada054` refactor: add control room panel view models (06-30)
- `71c96f2` refactor: replace server snapshots with data refresh (06-30)

## Stage 3: web interface and polish, 2026-07-04 to 2026-07-14

v1.19.0 "Haul Web Controls" (07-04), v1.20.0 "Haul Web LAN Update", v1.21.0 "Station Travel Assist" (07-06), v1.22.0 (07-14). The /haul web page drives the backend over WebSocket, multi-leg haul web UI, then Spansh neutron route planning and a route travel routine.

- `e9cc78b` feat: wire haul web page to backend (07-04)
- `52f3ceb` feat: add multi-leg haul web UI (07-05)
- `feaead4` feat(routines): add fly_spansh_route neutron travel routine (07-13)

## Pause: 2026-07-14 to 2026-11-05

No code for almost four months. Only a docs pass on 09-12/13 (31 commits): README and user docs reworked around lan mode + web frontend, screenshots, demo video, ToS automation warning (`841eb3a`, `75079bc`).

## Stage 4: refinement and breadth, 2026-11-05 to 2026-11-10

v1.22.1 "User Docs Refresh" (11-05) to v1.32.0 "Own Markets in EDDN" (11-11). Haul safety (buy top-ups, balance cap, TTS warnings), haul stats history (v1.23), background input plus Linux uinput and Steam Deck support (v1.24, v1.25), Piper TTS voices (v1.26), live config reload, a /controls web button board (v1.27), an EDDN market listener with a /routes trade route finder and /markets best-deal picks (v1.28, v1.29), safer FSD departure (v1.30).

- `e03e7af` feat: add uinput input backend for Linux (11-08)
- `0cfdfba` feat: add web /controls button board for single routines (11-09)
- `8f29edb` feat: add EDDN trade route finder and /routes page (11-10)

## Stage 5 (now): hub mode, 2026-11-11 to now

All in about two days. v1.33.0 "Hub Control Room and Travel Page", v1.34.0 "Hub Command Centre", v1.35.0 "Hub and Peer Commands" (all 11-11). A hub Control Room owns route search and the market DB; peers link to it via an outbox, hub pages view and drive any peer, the hub voices a picked node's TTS, mDNS / dns-sd discovery. It reuses the stage 2 WebSocket link and the stage 2.5 hydrate model. Then cleanup: v1.37.0 "edcr Package and CV Removal" (11-12; computer vision removed, routines are journal-only), v1.38.0 (11-12).

- `22dff4f` feat: add [hub] config for pointing a Control Room at a home hub (11-11)
- `e660b0c` feat: link peers to the hub with an outbox (11-11)
- `61fa66a` feat: find the hub on the LAN over mDNS and remember it (11-11)

Rust: none in the repo yet. Moving the stable parts to Rust is a future plan.

## Other notes

- Cross-platform from early on: Windows input backend in week 2 (v1.5.0), Linux/Steam Deck in November.
- CV removal (v1.37.0) is a notable simplification: the project committed to journal + Status.json only.
- The process itself is versioned: status handoff files and per-session iteration logs (split by area on 06-11), CI with Discord failure alerts.
