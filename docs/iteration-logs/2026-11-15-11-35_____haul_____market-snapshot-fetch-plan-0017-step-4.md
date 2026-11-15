# Iteration Log

- Area: `haul`
- Title: `market-snapshot-fetch-plan-0017-step-4`
- Started: `2026-11-15 11:35`

## Summary

- Plan 0017 step 4 built (client side), with the step 5 player doc lines done in passing. Config: `[eddn] snapshot_url` (the manifest URL; empty, the default, turns the feature off) and `snapshot_refresh_hours` (default 3, must be positive), in `defaults/eddn.toml`, `config.example.toml` and `docs/user/trade-routes.md`. Hub and standalone only; a peer has no store and asks the hub.
- Import is `EddnStore.import_database(path, min_updated_at=...)`: ATTACH the decompressed snapshot and apply every table's newest-wins rule in set-based SQL in one transaction under the store lock. A market only moves when the snapshot's row is strictly newer, and then all its prices are replaced; system, station, carrier_access, carrier_name use `>=`; carrier_seen and carrier_scan use `>` with the sighting rules. Markets older than `max_age_days` are skipped. A test imports the same fixture both ways (row-by-row `save` and the snapshot import) and compares every table row for row.
- Fetch (`edcr/market_snapshot.py`): `read_manifest` refuses a `schema` other than `SCHEMA_VERSION` before any download; `download_snapshot` streams the gzip, hashing the compressed bytes while decompressing into a temp file, and rejects a sha256 or byte-count mismatch with the DB untouched; `fetch_and_import` skips the download when the manifest `file` is the one already imported. Standard library only (`urllib`, `gzip`, `hashlib`); `urlopen` is injected.
- Background refresh (`edcr/market_snapshot_refresh.py`), thread `market-snapshot`: at start, fetch once when the DB is empty or its newest market is over 1 h old; without a listener, re-check the manifest every `snapshot_refresh_hours` and download only when `file` changed; with the listener on, no timer. Wired into `serve` (hub/standalone, logger `edcr.eddn`) and the local TUI (activity log). One log line per fetch with size, data age, counts and seconds; errors are one warning line and the loop keeps running. A late download never touches a closed store.
- `/api/eddn-status` now always carries `store` counts and a `snapshot` block (`mode` off / startup_only / timer, last check and fetch, file, data age, counts, next check, last error) whenever a store exists; `enabled` still means the listener runs. The Routes EDDN panel shows `snapshot, <n> markets, <age> old` without a listener, adds `snapshot <age>` beside a live listener, and logs one activity line per finished fetch.
- Measured on a frozen copy of the hub DB (source read-only, imports into scratch stores): 25,018 markets and 2,065,946 prices imported into an empty store in 1.01 s; re-importing the same file took 0.46 s with zero market or price changes and identical store counts. The plan's "1.5M rows, not yet timed" is replaced.
- On demand: `uv run python3 tools/market_snapshot.py fetch <manifest_url> <db_path> [--max-age-days N]`.

## Changes

- New: `edcr/market_snapshot_refresh.py`, `tests/test_market_snapshot_fetch.py`, `tests/test_market_snapshot_refresh.py`. Changed: `edcr/eddn/store.py` (`SnapshotImport`, `import_database`), `edcr/market_snapshot.py` (manifest, download, fetch), `tools/market_snapshot.py` (`fetch`), `edcr/config.py`, `defaults/eddn.toml`, `config.example.toml`, `edcr/control_room/server/serve.py` and `server/app.py` (status payload), `edcr/control_room/app.py` (TUI wiring), `web/routes.js`, `tests/test_config.py`, `tests/test_control_room_server.py`, `tests/test_hub.py`, plan 0017 (Status, Importing, steps 4 and 5), `docs/status/haul.md`, `docs/user/trade-routes.md`.
- Suite: 1230 tests (1 skipped without `EDCR_TEST_BOTO3`). Worker measured 0.725 s against a 0.738 s budget; on the secondary's busier machine 0.78 to 0.81 s, with the baseline already at 0.73 to 0.79 s before this step. The 16 new fetch/refresh tests take 46 ms in total; the two slowest in the suite are now the fetch CLI failure test (13 ms) and the real-HTTP stream test (10 ms).

## Follow-ups

- Step 3 (status Worker and Discord alarm) and the real deployment (bucket, token, domain, VPS) remain. Once the manifest URL exists, turning the feature on is one line in `config.toml` and a restart.
- The last imported file name lives in memory only, so a restart with a stale DB re-downloads one snapshot; acceptable at hourly publishes.
- A flattened snapshot carries only the final state: `carrier_seen` completeness is inferred from a matching `carrier_scan` timestamp, so an older complete scan that a later scan overwrote cannot be rebuilt. The VPS source has no journal scans, so this does not affect the hosted path.
- The suite sits over the time budget on a loaded machine. The next test-touching session should trim the fetch CLI failure test and the slowest hub and control room tests.
