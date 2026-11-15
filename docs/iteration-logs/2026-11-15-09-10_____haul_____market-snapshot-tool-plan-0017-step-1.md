# Iteration Log

- Area: `haul`
- Title: `market-snapshot-tool-plan-0017-step-1`
- Started: `2026-11-15 09:10`

## Summary

- Plan 0017 (hosted market snapshot) moved from thought experiment to scheduled work: the user approved its Decisions on 2026-11-15 and decided the refresh policy (VPS publishes hourly; clients without a listener refresh every 3 h by default, configurable; clients with a listener fetch once at start only when the DB is empty or the newest market is over 1 h old).
- Step 1 built: `tools/market_snapshot.py write <db_path> <out_dir>` (logic in `edcr/market_snapshot.py`) opens the source read-only, `VACUUM INTO` a temp file, gzip -9 to `markets-<YYYYMMDDTHHMMZ>.sqlite3.gz`, and writes `manifest.json` with file, created_at, newest_market_at, markets, prices, bytes, sha256, schema. Standard library only.
- `edcr/eddn/store.py` now owns `SCHEMA_VERSION = 1` and stamps `PRAGMA user_version` on stores still at 0; the manifest `schema` reads that constant and the snapshot copy is stamped too, so the step 4 client can refuse a mismatch. A source DB at another version is refused.
- Hub DB rows that are not from EDDN (own `Market.json` markets, `carrier_seen`, `carrier_scan`) are copied verbatim, not stripped: the `market` table has no source column and `carrier_seen` mixes EDDN and journal sightings, so a partial strip would mislead. Privacy comes from publishing only the VPS DB, which holds EDDN data only; documented in the module and the plan.
- Real run against the live hub DB (read-only, hub writing): 24,597 markets, 2.03M prices, 35.5 MB gzip, 6.8 s. The plan measured 27 MB on 2026-11-13; the DB has grown.

## Changes

- `edcr/market_snapshot.py`, `tools/market_snapshot.py`, `tests/test_market_snapshot.py` (new); `edcr/eddn/store.py` (`SCHEMA_VERSION`, user_version stamp).
- `docs/plans/0017-hosted-market-snapshot.md`: Status scheduled with step 1 built, refresh decision under Decisions, verbatim-copy note under Design > VPS, the two traffic Open points resolved, 2026-11-15 measurement. `docs/status/haul.md` Next bullet updated.
- Suite: 1207 tests in 0.689 s.

## Follow-ups

- Step 2 (publish to R2 plus the VPS systemd service and hourly timer), step 3 (status page and Discord alarm), step 4 (client fetch, import, 3 h refresh and the listener-on startup gap fetch), step 5 (docs).
- Existing hub DBs stay at `user_version` 0 until the hub next opens them with this code; the snapshot copy carries 1 regardless.
