# 0019: EDDN Routes on Haul and Route Recommendations

## Status

Built 2026-11-15. Automated behavior checks pass; deployment and live hub/forge validation below remain pending.

Approved step 1 deviation: server wiring resolves the viewed ship laden range only with `ship_range=1` (sent by `/haul`); an explicit query override wins and no ship retains the configured fallback. `/routes` defaults are unchanged. Search no longer selects/persists the first result automatically.

## Why

`/haul` finds two-way routes only through Inara, a Playwright scrape that stops at Inara's access check and is blocked when headless. Our own EDDN search (`/api/eddn-routes`, the `/routes` page) already ranks round trips from the market store and returns the `trade_route` object `/haul` imports. Market data also keeps arriving (EDDN, snapshot refreshes, our own Market.json), so a better route can appear while the pilot hauls without anyone searching again. The pilot should hear about it and pick it on the haul page with existing Select, Travel and Start route.

## Decisions (confirmed with the user)

- `/haul` searches EDDN only, through `/api/eddn-routes`. The Inara search UI goes away and there is no source select. The Inara code (`edcr/inara/`, `command.search_haul_routes`, `REQUEST_HAUL_SEARCH`) stays in the repo, uncalled by `/haul`.
- Never switch the selected route or start travel or haul automatically. The pilot always picks. This holds while a haul runs too.
- Search area is Global: one station-to-station route length cap over the whole store, no radius from the player.
- Jumps and trip time use the ship's laden range (`edcr/ship_range.py`), not `haul_search.toml`.
- The recommender checks every 300 s and searches only when the store or its inputs changed.
- A route qualifies when it beats the selected route by both +15% and +20m Cr/h. With no route selected, the top routes qualify.
- The page lists every qualifying route, up to a cap, each with Select, and says how many routes fell below the threshold.
- TTS speaks at most once per 300 s, any time, including mid-haul (no hold until docking). The page list updates silently between TTS lines.
- Peers are in v1. The hub computes for each linked node (forge runs the user's hauls) and for its own game, and each node voices its own recommendation.
- The recommender is on by default.

## Design

### Route length

- `/api/eddn-routes` takes the station-to-station cap as `max_route_ly` (`parse_route_query` in `edcr/eddn/route_query.py`). Without it the cap is `jumps × laden range` (`jumps` defaults to 4). `view=global` drops the origin radius and still reports each station's `ly_from_system` when the system is known.
- `/routes` Global offers the presets 100 Ly and 250 Ly. The recommender and `/haul` default to **100 Ly** (`[eddn.recommend] max_route_ly`). Profit per hour favours short routes anyway, and 250 Ly at bubble scale is the slower search ("global speed at bubble scale" is still an open `/routes` item).

### `/haul` search (EDDN only)

- The search form sends `view=global`, `max_route_ly` (the Route distance field, renamed Route length, Ly), `capacity`, `max_station_distance_ls`, `min_supply`, `surface` and `max_age_hours` to `/api/eddn-routes`. Blank fields fall back to `haul_search.toml` and the ship, as on `/routes`. On a hub page with a peer picked, `?node=` answers from the hub's store with that peer's ship, as `/routes` does today.
- Remove the Inara-only parts: `min_demand`, `metric`, the Inara Profit / hr line, Open in Inara and the access-check message. The origin field becomes "Distance from" (`system`), which only labels `<n> Ly away` per station.
- Each row's `trade_route` goes through the existing `routeFromApi`. Selecting a row, Copy / paste, Set destination, Travel, Start route and Track only stay unchanged. Rows carry EDCR `profit_per_hour` and `trip_s`, so `/haul` skips `/api/haul-trips` for them.
- Rows with `trade_route: null` (a commodity with no in-game name yet) stay listed, cannot be selected and say `commodity name unknown`. The result line repeats the `markets_left_out` counts as `/routes` does.

### Recommender (`edcr/route_recommend.py`, pure)

- Inputs: the Global search result for one node, that node's selected route, a baseline estimator, and the settings.
- The baseline is the selected route's Cr/h at current prices under the same model. Find the selected pair in the result by station + system names (TradeRoute has no market ids). Otherwise estimate it with `edcr/trade_trip.estimate_trip` on store facts, as `/api/haul-trips` does. Otherwise there is no baseline, and the list says "selected route not priced: <what is missing>" and applies only the no-selection rule.
- Qualifying: `trade_route` present, a different pair from the selected one, `cr_h >= baseline × 1.15` and `cr_h - baseline >= 20,000,000`. With no route selected, the top routes qualify.
- Output: `RouteRecommendations(routes=[... up to list_cap], below_threshold=n, name_unknown=n, baseline_cr_h, baseline_source, generated_at)`.
  - `list_cap` defaults to 10. "Below the threshold" counts routes in the search result that beat nothing. `name_unknown` counts routes that beat the threshold but lack a `trade_route`. Both show on the page.
- The search uses `limit=200` (the `parse_route_query` maximum), so the counts cover the top 200 routes. The page says "of the top 200".

### Where it runs

- On the hub and standalone, a `route-recommend` thread in `server/serve.py` runs only when the market store is open (never on a peer). Every `check_every_s` (300) it reads `EddnStoreCounts.newest_market_at` and each node's inputs. A node is recomputed when the store advanced or its inputs changed since its last run. The store covers the EDDN listener, snapshot imports and `game-markets` imports, since all three write the same store. A node's inputs are current system, ship id, hold, laden range and selected route.
- Nodes: the hub's own game (its data provider and `broker.server_state.selected_trade_route()`), and every connected peer from the registry `node_state`.
  - `node_state` (`edcr/hub/relay.py`) gains `selected_route`: from/to station and system, the two commodities. A peer with no ship state is skipped and logged once.
  - `haul_search.toml` is the hub's own for every node, as with `/api/eddn-routes?node=` today, since peer defaults are not published. The time model is `time_models.active(ship_id)` per node.
- Delivery: the hub's own result goes straight to its local handler. A peer's result goes down the link as a `route_recommendation` frame (like `voice_mute`) with the JSON payload. A peer never computes.

### Node side (the same code on hub, standalone and peer)

- It stores the latest `RouteRecommendations` in `server/state.py` and publishes it in hydrate as `route_recommendations`. A hub page viewing a peer gets it through the relayed hydrate.
- Dismissed keys live on the node. The key is (station 1, station 2, outbound commodity, inbound commodity). They clear when the selected route changes. Dismissed routes leave the list but are counted (`dismissed: n`).
- TTS: when the best undismissed route's key, or its Cr/h by another 15%, differs from the last spoken one, and 300 s have passed since the last recommendation TTS, it announces `AnnouncementId.ROUTE_RECOMMENDED` through `_announce_tts`. That path publishes it, so browser `speech.js`, the hub voice when this node is voiced, and Mute all apply as for any callout. The phrase in `defaults/tts.toml`:
  - `route_recommended = "{count} better routes. Best: {from_station} to {to_station}, about {gain_short} per hour more."`
  - With one route, `{count}` reads "One better route". With no selected route, the `{gain_short}` part is replaced by `{cr_h_short} per hour`.
  - It can be turned off with `tts.disabled_messages`.

### `/haul` card

- A **Better routes** panel at the top of the Route panel lists each route with: from → to, commodities, EDCR Cr/h, `+X% / +Y m/h` over the selected route, jumps and Ly, price age, and Select / Dismiss buttons.
- Footer: `n below threshold of the top 200, n names unknown, n dismissed`, plus when it was checked (`EDDN, checked 3 min ago`).
- **Select** sends the existing `command.select_trade_route` with that route's `trade_route` (persisted, hydrate refreshes, the Travel target fills). The pilot then presses Travel, Start route or Track only. A running haul still refuses Start route (`check_routine_ready`), so switching mid-haul is Stop after run, then Start route.
- **Dismiss** sends `command.dismiss_route_recommendation` with the key.
- The panel is hidden when the list is empty and nothing was dismissed. It shows "No better route (n below threshold)" after a check that found none.

### Settings (`[eddn.recommend]` in `defaults/eddn.toml`, `EddnConfig`)

`enabled = true`, `check_every_s = 300`, `max_route_ly = 100`, `min_gain = 0.15`, `min_gain_cr_h = 20000000`, `list_cap = 10`, `tts_gap_s = 300`.

## Build steps

Each step is one worker commit with its tests (`uv run python3 -m unittest discover -s tests`, behavior tests with plain function fakes).

1. **`/haul` searches EDDN.** `web/haul-ui.js`, `web/haul-v1.html`: the search calls `/api/eddn-routes` with `view=global` and the fields above. Remove the Inara form fields, the Profit / hr Inara line and the Open in Inara link. Name-unknown rows are not selectable. `defaults/haul_search.toml` gains nothing new; `max_route_distance_ly` stays the laden-range fallback for `/routes`. Server adds the approved `ship_range=1` opt-in described above. Check: a look-only `/haul` (no `#route=`) in a browser, then select and Copy a row.
2. **Recommender core.** `edcr/route_recommend.py` with `route_key`, `recommend(...)` and `RouteRecommendations` (to/from JSON). Tests in `tests/test_route_recommend.py`:
   - both thresholds (only one met fails)
   - no selected route lists the top `list_cap`
   - the selected pair is excluded
   - the baseline found in the result vs the `estimate_trip` fallback vs missing inputs
   - the counts for below threshold and name unknown
3. **Settings.** `[eddn.recommend]` in `defaults/eddn.toml` and `edcr/config.py`. Tests: defaults load, and `config.toml` overrides.
4. **Node side: state, hydrate, dismiss, TTS.** `server/state.py`, hydrate payload, `command.dismiss_route_recommendation` in `server/app.py`, `AnnouncementId.ROUTE_RECOMMENDED` in `edcr/tts.py`, the phrase in `defaults/tts.toml`, and a `RecommendationAnnouncer` (injected clock) applying dismissed keys, repeat keys and the 300 s gap. Tests:
   - one announcement for a new best
   - none within 300 s
   - a repeat key is silent unless 15% better
   - a dismissed route is dropped and counted
   - dismissals clear on a new selected route
   - hydrate carries the list
   - a disabled message is not published
5. **Hub loop for its own game.** A `route-recommend` thread in `server/serve.py` (hub/standalone with a store, `enabled`), with injected `time_fn`, `store_counts`, `node_inputs()`, `run_query` (wraps `parse_route_query` + `run_route_query` with `view=global`, `max_route_ly`, `limit=200` and the ship's laden range) and `deliver(node_id, recs)`. Tests with fakes:
   - no search when the store and inputs are unchanged
   - a search on a store advance or an input change
   - the per-node time model and laden range are passed through
6. **Peers.** `selected_route` in `node_state` (`edcr/hub/relay.py`), the loop iterating connected registry nodes, the `route_recommendation` link frame sent by the hub, and the peer's handler feeding step 4's node side. Tests:
   - a fake registry with two peers gets one frame each
   - a peer without ship state is skipped
   - a peer frame turns into hydrate plus one announcement
   - an older peer that ignores unknown frames does not break the link
7. **`/haul` Better routes panel.** `web/haul-ui.js`, `web/haul-v1.html`, `web/haul-ui.css`: render `route_recommendations`, Select via `command.select_trade_route`, Dismiss, the footer counts, and phone layout. Tests: a server round trip where Select stores the route and Dismiss removes it from the next hydrate. Check: a look-only browser view, plus a hub page with a peer picked.
8. **Docs.** `docs/user/trade-routes.md` (`/haul` is EDDN-only, recommendations, settings), `docs/user/hub.md` (the hub computes for peers), `docs/status/haul.md`, `docs/status/control-room.md`, an iteration log.

## Rejected ideas (with the user's reasons)

- A Source select on `/haul` (EDDN | Inara): `/haul` drops Inara instead. The code stays.
- Near view, 4 jumps around the current system: Global with a route length cap instead.
- A single best-route card: a list of every route that beats the selected one.
- Holding TTS until docking at station 1: speak any time, rate-limited.
- Peers as a follow-up: in v1, since the user's hauls run on a peer.
- Triggering on every EDDN message: too frequent; a 300 s check gated on store changes.

## Open points

- Measured the real local hub store read-only: 100 Ly 4.531 s; 250 Ly 18.271 s (1,895 eligible markets, 200 results, 720 t / 31.5 Ly fixture ship inputs). Keep the approved 100 Ly default.
- A peer's Better routes panel needs the hub. While the link is down, the panel keeps the last list with its check time and a "hub unreachable" note, and no new TTS plays.

## Validation

Automated: 1,271 tests in 0.946 s, OK (1 skipped); slower than the 0.7626 s suite budget, as before this work. Timing report identifies the Node full-script web flow (~68 ms) and existing four transit tests (~34–36 ms each). Mocked Chromium `/haul?node=forge` at 1440 px and 390 px had no page errors or overflow. Actual hub/forge deployment checks below remain pending; no game input was sent.

- `/haul` on the hub and on forge (through the hub) lists EDDN routes, and Select, Travel and Start route run as before.
- Selecting a weak route leads to a Better routes list and one TTS line within about 300 s. No second line follows within 300 s, and none for the same route.
- During a running haul on forge, a recommendation is spoken and listed, the selected and running route stay unchanged, and Start route stays refused until the haul stops.
