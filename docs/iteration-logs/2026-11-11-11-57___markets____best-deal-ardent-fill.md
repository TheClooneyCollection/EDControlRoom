# Iteration Log

- Area: `markets`
- Title: `best-deal-ardent-fill`
- Started: `2026-11-11 11:57`

## Summary

- Best deal asks Ardent Insight for station and system details the EDDN store and journal lack, so profit per hour shows for stations never docked at and systems never visited. This builds plan 0014 slice 3 for these fields.

## Changes

- `edap/ardent.py`: `ArdentLookup` is a `FactLookup` (last in the source order). It fetches `GET /v2/system/name/{name}/stations` once per system (`marketId`, `stationName`, `stationType`, `distanceToArrival`, `maxLandingPadSize`, `systemAddress`, `systemX/Y/Z`, `updatedAt`, verified live 2026-11-11 against Chelgit: Humboldt Hub 5.67 Ls, Ocellus, pad 3) and falls back to `GET /v2/system/name/{name}` for coordinates. Station match by market id, then name.
- Requests: 3 s timeout, `EDControlRoom/<version> (Best deal lookups)` User-Agent, an unknown system (404) is an empty answer; any failure logs once, returns nothing (the page keeps "-") and is retried after 10 minutes. The fetch is injected (`httpx_fetch_json` in production, fakes in tests).
- `serve.py` writes found rows into the EDDN store through `store_saver(eddn.store.apply, eddn.store.commit)` (the listener's own connection and lock, newest `updatedAt` wins), so `/routes` gains those coordinates and stations; without EDDN the rows stay in the lookup's memory cache.
- `build_observer_server_app(ardent_lookup=...)` adds it to `/api/market-compare` sources after the journal; it is asked only while an input is still missing.

## Follow-ups

- `/routes` skips markets without coordinates and does not call Ardent itself: filling them would mean one request per uncovered system per search. Possible later: a background fill of uncovered systems.
- A system is fetched once per server run; a station added to it later needs a restart (or EDDN) to appear.
