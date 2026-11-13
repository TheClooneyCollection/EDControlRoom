# 0017: Hosted Market Snapshot for a First Run

## Status

Proposed (2026-11-13). Not started; the user is still deciding whether to publish the data at all.

## Why

A fresh install opens an empty market DB (`.eddn_markets.sqlite3`), so `/routes` and Best deal have nothing to rank until the EDDN listener has run for hours. A hosted copy of a hub's DB would give a new player useful routes within seconds of the first start.

Measured on the Mac hub DB, 2026-11-13: 18,985 markets, 1.56M prices, all within the 7 day `max_age_days`, 7,645 updated in the last 24 hours. `VACUUM INTO` gives 70 MB; gzip -9 gives 27 MB, zstd -19 gives 21 MB.

## Design

### Hosting

- A rolling GitHub Release on a fixed tag (for example `market-snapshot`), its assets replaced with `gh release upload --clobber`. Served from GitHub's CDN, free, 2 GB per asset; 27 MB downloads in seconds.
- Assets: `markets.sqlite3.gz` and a small `manifest.json` (`created_at`, `newest_market_at`, `markets`, `prices`, `bytes`, `sha256`, `schema`).
- Move to Cloudflare R2 (free egress) only if traffic or a custom domain needs it.

### Publishing (hub)

- The snapshot must come from a long-running listener; a GitHub Actions job cannot gather days of EDDN data, so the hub publishes it.
- A tool, then a timer on the hub every few hours: `VACUUM INTO` a temp file, strip personal data (below), gzip, write the manifest, upload both.
- gzip, not zstd: the standard library reads it, and zstd needs a dependency before Python 3.14 for a 6 MB saving.

### Importing (client)

- On start, when the DB is empty (or on demand, for example `tools/market_snapshot.py fetch`), read the manifest, stream the `.gz` while decompressing, check the sha256, then import.
- The import uses the existing rule: newest timestamp wins and a newer snapshot replaces the whole station, so it never overwrites fresher local data and an existing DB can use it to fill gaps.
- Skip markets older than `max_age_days`; refuse a manifest whose `schema` does not match.
- Peers do not fetch; they ask the hub as today.

### Personal data

- The DB holds our own recorded markets (from `Market.json` via `game-markets`) and `carrier_seen` / `carrier_scan` rows from our journal, which show where and when the pilot docked.
- `market` has no source column, so own markets cannot be stripped today. Either add a source column (EDDN vs journal) and publish EDDN rows only, or accept that a docked market looks like any other EDDN market (the game uploads the same data through other tools).
- Drop `carrier_scan` and `carrier_seen` from the published copy; departed carrier hiding then starts from the client's own sightings.

## Build steps

1. Snapshot tool: `VACUUM INTO`, strip personal tables, gzip, manifest; local only, no upload.
2. Publish: upload to the rolling release, plus the hub timer.
3. Client fetch and import, on an empty DB and on demand, with the size and age shown in the log and the EDDN listener panel.
4. Docs: `docs/user/trade-routes.md` and the haul status.

## Open points

- Publish at all: the data goes public once uploaded. EDDN is a public feed and Spansh and Inara redistribute it, but the user decides.
- Strip own markets with a source column, or accept them.
- How often to publish (every few hours vs daily) and whether a client refreshes an existing DB from it.

## Validation

- A fresh checkout with no DB fetches the snapshot and `/routes` shows Near and Global results without the listener.
- Importing into a DB with fresher local rows leaves those rows untouched.
- A corrupted download (bad sha256) is rejected and the DB is unchanged.
