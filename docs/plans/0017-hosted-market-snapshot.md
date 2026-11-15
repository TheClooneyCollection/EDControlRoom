# 0017: Hosted Market Snapshot for a First Run

## Status

Scheduled; Decisions approved 2026-11-15. Step 1 built 2026-11-15: `tools/market_snapshot.py write <db_path> <out_dir>` (local snapshot and manifest). Step 2 built 2026-11-15: `tools/market_snapshot.py publish`, optional boto3 upload, status JSON and VPS deployment templates (validated locally; no live deployment yet). [Plan 0018](0018-static-routes-website.md) builds a static routes website on the same setup.

## Why

A fresh install opens an empty market DB (`.eddn_markets.sqlite3`), so `/routes` and Best deal have nothing to rank until the EDDN listener has run for hours. A hosted copy of a full DB would give a new player useful routes within seconds of the first start, and keeps a player who has not run EDCR for a while from starting on stale or pruned data. If EDCR is ever downloaded widely, every new install needs this starting data at once.

Measured on a hub DB, 2026-11-13: 18,985 markets, 1.56M prices, all within the 7 day `max_age_days`, 7,645 updated in the last 24 hours. `VACUUM INTO` gives 70 MB; gzip -9 gives 27 MB, zstd -19 gives 21 MB.

Measured again with the step 1 tool on the same hub DB, 2026-11-15: 24,597 markets, 2.03M prices, 35.5 MB gzip, 6.8 s read-only against the live WAL file while the hub kept writing.

## Decisions (confirmed with the user)

- A VPS runs the listener and publishes; Cloudflare R2 stores and serves the snapshot. Downloads go out through Cloudflare, not the VPS.
- Public: anyone can download the snapshot, with no token. It is the starting data for every install (2026-11-13).
- Refresh policy (2026-11-15): the VPS publishes hourly. With the listener off (default), clients refresh every 3 h by default, configurable. With the listener on, there is no periodic refresh: at start only, fetch once if the DB is empty or its newest market is over 1 h old, then let the listener keep it current.
- The snapshot replaces each client's own listener: a client keeps its DB current by fetching new snapshots in the background, so `eddn.enabled` stays `false` by default and the listener stays an opt-in for players who want live data.
- Full snapshots only, no delta packs (2026-11-13). The VPS DB already holds the newest copy of every market within 7 days, each upload replaces the full file, and 27 MB is small enough to download whole every time. Deltas would add a base/delta chain to build and test for a few MB saved.

## Design

### VPS

- Runs the EDDN listener (`tools/eddn_listen.py`, or the server with `eddn.enabled = true`) on its own DB. The store keeps only the newest copy of each market and `EddnService` prunes markets older than `max_age_days`, so the DB is always the last 7 days.
- The VPS is not a hub and takes no peer pushes, so its DB holds EDDN data only: no own `Market.json` markets and no `carrier_seen` / `carrier_scan` from a pilot's journal.
- Snapshots copy the database verbatim; no tables or rows are stripped. Privacy comes from publishing only the VPS database holding EDDN data only, never a hub database.
- A systemd timer hourly: `VACUUM INTO` a temp file, gzip, write the manifest, upload the gzip, status JSON and finally the manifest through the S3 API using boto3 (optional `publish` extra, imported only for real uploads), with a token scoped to the bucket. Deploy templates: `deploy/market-snapshot/`; [operator guide](../operators/market-snapshot-vps.md).
- gzip, not zstd: the standard library reads it, and zstd needs a dependency before Python 3.14 for a 6 MB saving.
- Repo docs name only "a VPS"; no host names or addresses.

### R2 and the CDN

- Served from a custom domain on the bucket, so Cloudflare's cache fronts it; the `r2.dev` URL is rate-limited and not meant for production.
- Snapshot file names carry the time (`markets-20261113T2300Z.sqlite3.gz`) and are cached as `immutable`; `manifest.json` has a short TTL (about 60 s) and holds `file`, `created_at`, `newest_market_at`, `markets`, `prices`, `bytes`, `sha256`, `schema`.
- An R2 lifecycle rule deletes snapshots older than a few days.
- R2 egress is free; the free tier's storage and write operations cover a few uploads a day.

### Status page and alarm

- The checks run outside the VPS, so a dead VPS still raises the alarm.
- Each upload also writes `status.json`: newest market time, markets updated in the last hour, disk free and DB file size. `messages_per_minute` is null with a note until listener counters are persisted.
- A Cloudflare Worker on the same domain serves `/status` from `manifest.json` and `status.json`: snapshot age, newest market age, markets, prices, size, listener rate.
- A Worker Cron Trigger every 15 minutes alerts a Discord webhook when the snapshot is over 3 hours old or the newest market has not moved for an hour (the listener stalled while uploads still run), and again when it recovers.
- Fallback if the Worker is too much: healthchecks.io pinged by the VPS after each upload, which catches a dead VPS but not stale data unless the VPS checks freshness before pinging.

### Importing (client)

- On start, when the DB is empty (or on demand, for example `tools/market_snapshot.py fetch`), read the manifest, stream the `.gz` while decompressing, check the sha256, then import.
- The import uses the existing rule: newest timestamp wins and a newer snapshot replaces the whole station, so it never overwrites fresher local data and an existing DB can use it to fill gaps. Re-importing the same file changes nothing.
- With the listener off, refresh every 3 h by default (configurable) in the background while the Control Room runs: read the manifest on a timer and download only when `file` changed. With the listener on, check only at start and fetch once when the DB is empty or the newest local market is over 1 h old (after time offline); the listener keeps it current after that.
- Import on a background thread so start-up and pages never wait on it (1.5M rows, not yet timed).
- Skip markets older than `max_age_days`; refuse a manifest whose `schema` does not match.
- Peers do not fetch; they ask the hub as today.

## Build steps

1. Built 2026-11-15: snapshot tool (`tools/market_snapshot.py write`): `VACUUM INTO`, gzip, manifest; local only, no upload.
2. Built 2026-11-15: `tools/market_snapshot.py publish` uploads to an S3-compatible bucket; `--dry-run` writes local artifacts and lists uploads. VPS systemd services, timer and env template in `deploy/market-snapshot/`, [operator note](../operators/market-snapshot-vps.md). Local S3 stand-in verified; real R2/VPS deployment pending.
3. Status Worker: `/status` page and the cron alarm to Discord.
4. Client fetch and import, on an empty DB, on demand and on the background refresh timer, with the size and age shown in the log and the EDDN listener panel.
5. Docs: `docs/user/trade-routes.md` and the haul status.

## Rejected ideas (with the user's reasons)

- Delta packs (a daily base plus hourly cumulative deltas): rejected; the full file is always current and small enough (27 MB) to download whole, and deltas add a base/delta chain to build and test.
- A token-gated or private snapshot: rejected; the point is starting data for every install, including a sudden wave of new players.
- Turning `eddn.enabled` on by default: not needed; background snapshot refreshes keep a client's DB current without its own listener.
- Free always-on hosts for the listener (Oracle Cloud Always Free, a Google Cloud e2-micro, back-to-back 6 hour GitHub Actions jobs): set aside for an existing VPS; the Actions relay also sits in a grey area of GitHub's terms.
- The hub publishing its own DB: replaced by the VPS, which holds EDDN data only, so no pilot's own markets or carrier sightings go public.
- A rolling GitHub Release as the host: kept only as a fallback; R2 behind a custom domain has free egress and Cloudflare's cache.

## Open points

- How often to publish, resolved 2026-11-15: hourly (about 650 MB a day uploaded from the VPS), see Decisions. Revisit only if the VPS traffic allowance turns out tight.
- Client traffic resolved 2026-11-15: refresh every 3 h by default only without a listener (about 216 MB/day at 27 MB per snapshot); with a listener, only the startup gap fetch described in Decisions.

## Validation

- A fresh checkout with no DB fetches the snapshot and `/routes` shows Near and Global results without the listener.
- Importing into a DB with fresher local rows leaves those rows untouched.
- A corrupted download (bad sha256) is rejected and the DB is unchanged.
- A client with the listener off picks up a new snapshot within one refresh interval.
- Stopping the VPS listener or uploads raises the Discord alarm within the thresholds, and the recovery message follows.
