# Iteration Log

- Area: `haul`
- Title: `eddn-routes-page`
- Started: `2026-11-10 15:15`

## Summary

- Plan 0014 route finder and `/routes` page, on the EDDN SQLite store. Live check on 147 eligible markets: near and global searches run in 0.04 to 0.1 s, top route Di Fiore Meteor Manor ↔ Braddocks Hide (gold / marine supplies, 1 jump) (before calibration it estimated 165M/h; with the fitted model 116M/h at a 780s round trip).

## Changes

- `edap/eddn/routes.py`: `load_route_markets` (skips carriers, construction depots, too-small pads with type-based pad fallback, surface unless opted in, far stations, stale markets; coordinates by system address or name), `best_leg` (hold capped by capacity and stock, demand only filtered), `find_routes` (spatial grid with cell = range, near view keeps station 1 within the origin radius, ranked by profit/hour), `TimeModel` fitted on 125 November journal legs (Undocked to Docked plus docked time): 90s docked + 110s + 170s first jump + 65s per extra jump + `13 × Ls^(1/3)`; Voltaire ↔ Melroy comes out at 880s against ~816s per run plus ~90s docked at station 1.
- `edap/eddn/route_query.py`: query parsing with `haul_search.toml` and ship fallbacks (`max_route_distance_ly` is the laden jump range), read-only DB run, JSON payload.
- Legs carry in-game names from recent-market snapshots (191 of 210 EDDN commodities named; the rest are salvage and illegal goods). Each route has a `trade_route` JSON (null when a name is unknown) that the `/routes` Copy button puts on the clipboard for the `/haul` paste box.
- `GET /api/eddn-routes` and web `/routes` (Near/Global, 1/2/4 jumps, 100/250 Ly, filters), linked from every sidebar.
- `/markets`: Best deal panel moved to the top; fixed the Save token button adding another 30 s refresh timer on every click.

## Follow-ups

- Not yet opened in a browser; check `/routes` and a Copy → `/haul` paste live.
- Check global speed once the DB covers the bubble; add Ardent lookups for markets without coordinates.
