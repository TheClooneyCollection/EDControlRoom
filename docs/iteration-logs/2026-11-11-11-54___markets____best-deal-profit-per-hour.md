# Iteration Log

- Area: `markets`
- Title: `best-deal-profit-per-hour`
- Started: `2026-11-11 11:54`

## Summary

- The `/markets` Best deal panel now shows Inara's trade route numbers: profit per ton, profit per trip (full-hold round trip) and estimated profit per hour, plus measured profit per hour from completed haul runs on the same station pair.

## Changes

- `edap/eddn/routes.py`: `jump_count` and `round_trip_s` are the shared helpers `/routes` (`_route`) and Best deal both use, so the two pages agree on trip time.
- `edap/eddn/route_query.py`: `laden_jump_range` (query, then `haul_search.toml` `max_route_distance_ly`, then 17.2) is shared by `/api/eddn-routes` and `/api/market-compare` (`laden_jump_range_ly=`).
- `edap/trade_trip.py`: `gather_facts` fills coordinates, distance from star and station type per station from ordered sources (EDDN store, then journal), asking a later source only while something is missing; `estimate_trip` returns jumps, distance and `trip_s`, or `trip_s` null with a `missing` list (same-system pairs need no coordinates). The 1000 Ls default in `TimeModel.supercruise_s` is never used here: no guessing.
- `edap/recent_markets.py`: the recent markets store also keeps journal `places` (stations: `DistFromStarLS`/`StationType` from `Docked`, or `Location`/`CarrierJump` while docked; systems: `StarPos` from `FSDJump`/`Location`/`CarrierJump`), 50 of each, newest first. Recorded live in `ControlRoomApp._handle_event` and from the latest journal at startup (`bootstrap.record_journal_places`). Market.json's `StationType` is the journal fallback for station type.
- `edap/haul_history.py`: `RunTotals` gains `duration_s`, so each route summary has its own haul time; `/haul` History Routes shows a Completed / hour column. `measured_route` adds completed runs of the pair in either direction, case-insensitive, with recorded systems required to match.
- `web/markets.js`: per-hour is computed in the browser from the picked deals (`perTrip * 3600 / trip.trip_s`), shown with trip minutes, jumps each way and distance; a missing input shows "-" with the names of what is missing. Copy route / Open in haul now carry `profit_per_hour`.

## Follow-ups

- Hub peers push only markets to the hub, not journal places; Best deal reads the local store anyway.
