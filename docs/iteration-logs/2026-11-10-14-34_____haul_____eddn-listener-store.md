# Iteration Log

- Area: `haul`
- Title: `eddn-listener-store`
- Started: `2026-11-10 14:34`

## Summary

- Plan 0014 slices 1 and 2: an EDDN relay listener and a latest-snapshot SQLite price store, runnable standalone with `uv run python3 tools/eddn_listen.py`.

## Changes

- `edap/eddn/messages.py`: parses live `commodity/3` and `journal/1` Docked/CarrierJump/FSDJump/Location; drops `/test` schemas, legacy-galaxy uploads (`CAPI-Legacy`, game 2.x/3.x) and price rows the station neither sells nor wants. Carriers are flagged by `FleetCarrier` type or `XXX-XXX` callsign; market ids cannot tell them apart (colonisation stations also exceed 3.7 billion).
- `edap/eddn/store.py`: `system`, `station`, `market`, `price` (WITHOUT ROWID) tables in WAL mode; a newer snapshot replaces a market's prices, older ones are ignored; station updates keep known distance/pad when a message omits them; `prune` drops markets older than `eddn.max_age_days`.
- `edap/eddn/listener.py`: background thread, commits about once a second, prunes hourly, reconnects after 60s of silence, counts messages/updates/errors.
- New `[eddn]` config (`defaults/eddn.toml`): `enabled` (not used yet), `relay`, `database_file` (default git-ignored `.eddn_markets.sqlite3`), `max_age_days`. New dependency `pyzmq`.
- Live check: about 11 relay messages a second overall, about one market snapshot every 2 seconds.

## Follow-ups

- Run the listener inside the Control Room server when `eddn.enabled`, then slices 3 to 6 (Ardent lookups, route finder, profit-per-hour model, `/routes`).
