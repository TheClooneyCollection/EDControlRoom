# Iteration Log

- Area: `control-room`
- Title: `cheapest-markets-build`
- Started: `2026-11-27 17:49`

## Summary

- Built plan 0022 (M7) in four slices on branch `m7-cheapest-markets`: `/cheapest` page and `GET /api/cheapest-markets`. Not yet tried against a live hub or game.

## Changes

- A `edcr/cheapest_markets.py`: query parsing with ship defaults, hub store query (first failing rule counted in `hidden`), merge by `market_id`, suspect carrier price flag, payload. `UnknownSystemError` (a `ValueError`) when the reference system is unknown and Spansh is off.
- B `edcr/spansh_stations.py`: price-sorted Spansh station search. Live checks: a min-only supply filter needs `{"comparison":">=","value":N}`; the age range goes in as ISO timestamps; station types seen are Asteroid base, Coriolis Starport, Orbis Starport, Outpost, Mega ship. The age range is added in `search_cheapest` because `spansh_search_body` has no `now`.
- C `edcr/ship_types.py` pad table, `REQUEST_CHEAPEST_MARKETS`, the endpoint in `app.py`; peers forward resolved params, the hub alone calls Spansh, and a Spansh failure keeps hub rows. An unknown pad config falls back to `L`.
- D `web/cheapest.html`/`.js`, nav entry, page route; the JS test runs the page script in Node and skips when Node is missing.
- The full suite stays over the 0.0007 s per test budget, as `main` was before this work (about 0.00098 s per test). The Node page test costs about 0.08 s.

## Follow-ups

- Live check: `/cheapest` for Tritium near the current system, then `node=<peer>`.
- Decide whether to speed up the slowest existing haul web tests to meet the budget again.
