# EDDN Listener for Haul Routes

Date: 2026-11-10

Status: research only, no implementation decided.

Related: [0008](0008-inara-multi-centre-haul-sampling.md), [0009](0009-ardent-api-haul-source.md), [0010](0010-eddn-listener-haul-routes.md)

Note: The scratch listener (`listen.py`), pairing prototype (`roundtrip.py`) and the `run1/` capture were not kept in the repo.

Measured 2026-11-10, 12:17 to 12:32 UTC (a Tuesday midday, likely below evening peak), on the Mac.
Scratch code used for the measurement (not kept in the repo):
- `listen.py`: ZMQ SUB listener with stats and a SQLite latest-snapshot store
- `roundtrip.py`: pairs markets into two-way routes
- `run1/`: the 15-minute capture (`stats.json`, `samples.json` with one raw message per schema, `eddn.sqlite`)

## TL;DR

- Listening is trivial: one ZMQ SUB socket on `tcp://eddn.edcd.io:9500`, zlib + JSON. The listener used **0.22% CPU and 29 MB RSS** on the Mac, including SQLite upserts. It runs comfortably on the Deck next to the game.
- Volume: **9.8 msg/s (all schemas), 8.5 KB/s compressed (~730 MB/day), 27 commodity/3 markets/min (~39k market snapshots/day)**. EDDN latency from market timestamp to receipt was **p50 1.8 s, p90 5.1 s**.
- A latest-snapshot store is small. 15 minutes gave 228 markets, 35.8k price rows and a 1.6 MB DB. A day of active markets (~10k) is ~50 to 80 MB. Every market ever seen (~40k non-stale) is a few hundred MB.
- **The live anomaly the request asked for showed up during the test.** Crucis Sector FW-W b1-7 sells **Silver at ~3,450 cr** (Chauhan Dock 81k stock, Cranfield Plant 104k, Kutter Platform 691). Normal is ~33k buy, 41 to 49k sell. Payson Enterprise (Crucis Sector FM-V b2-1, 37.7 ly away) pays 48,859 with demand 12k. That is roughly **31M cr per 700 t trip**, ranked #1 by `roundtrip.py` from 15 minutes of data. Ardent shows Cranfield Plant at 3,481 since at least 11:51 UTC. The requester may want to act on this now. Chauhan Dock is a CraterOutpost (surface, L pad, 292 ls).
- Alternative to self-hosting: **Ardent Insight API** (`api.ardent-insight.com/v2`) is EDDN-fed and matched our capture timestamps to the second. It has per-system station metadata (coords, pad size, distance) and per-commodity endpoints. It is good for bootstrap and cross-checks, but polling it cannot push anomalies the way our own listener can.

## 1. How to listen

Docs: https://github.com/EDCD/EDDN/blob/live/docs/Developers.md, schemas at https://github.com/EDCD/EDDN/tree/live/schemas (`commodity-README.md`, `journal-README.md`, `commodity-v3.0.json`).

- Relay: `tcp://eddn.edcd.io:9500`, ZeroMQ **SUB**, subscribe to `""`. No server-side topic filtering (the docs say the relay runs an old ZMQ), so filter on `$schemaRef` client-side.
- Each frame is **zlib**-compressed (`zlib.decompress`, not gzip) UTF-8 JSON. Verified.
- Envelope: `{"$schemaRef", "header", "message"}`.
  - `header` fields: `uploaderID` (hashed), `softwareName`, `softwareVersion`, `gameversion`, `gamebuild`, `gatewayTimestamp` (set by the gateway).
  - `gameversion` is the journal version or `CAPI-Live-market` / `CAPI-Legacy-market`. **Drop Legacy** (3.8 client, separate galaxy state).
- **Drop `/test` schemas.** They appear on the live relay (~3% of traffic, e.g. `journal/1/test`).
- Gateway validates messages, so subscribers need not.
- Schemas that matter:
  - `commodity/3` message: `systemName, stationName, stationType?, carrierDockingAccess?, marketId, timestamp, horizons, odyssey, commodities[], economies?, prohibited?`.
  - Each commodity: `name, meanPrice, buyPrice, stock, stockBracket, sellPrice, demand, demandBracket, statusFlags?`.
  - `buyPrice` = player buys from station, `sellPrice` = player sells to station. Names are lowercase internal symbols (`silver`, `waterpurifiers`).
  - commodity/3 has **no coordinates and no pad size.**
  - `journal/1`: `FSDJump`, `Location`, `CarrierJump` carry `StarSystem, SystemAddress, StarPos`. `Docked` carries `MarketID, StationName, StationType, DistFromStarLS, LandingPads{Small,Medium,Large}, StarPos`. `Scan` is ~70% of journal/1 and is irrelevant.
  - `navroute/1` and `approachsettlement/1` also carry positions. `dockinggranted/1` and `dockingdenied/1` have pad info.
- Reconnect/heartbeat: EDDN has no heartbeat. ZMQ reconnects TCP automatically, but a silently dead link can just look quiet. Set these:
  - `TCP_KEEPALIVE=1` (plus `TCP_KEEPALIVE_IDLE`)
  - `RCVTIMEO` around 60 to 120 s. Traffic never stops: ~10 msg/s, never a 1 s gap seen.
  - On timeout, close the socket and connect again.
  - `RCVHWM` default is fine at this rate.
- Python: `pyzmq` only. Prefer one listener per host. Supervise it via systemd on the Deck (the user already uses `systemd-run` there).

## 2. Measured volume (900 s)

| metric | value | per day |
|---|---|---|
| all messages | 8,782 (9.76/s) | ~843k |
| compressed bytes | 8.5 KB/s | ~730 MB |
| decompressed | 27.2 KB/s | ~2.3 GB |
| commodity/3 | 406 (27.1/min) | ~39k snapshots |
| unique markets (15 min) | 228 | see below |
| commodities per snapshot | 161 avg | |
| journal Docked | 417 | ~40k (good metadata source) |
| FSDJump/Location/CarrierJump | 829 | ~80k (740 unique systems w/ coords in 15 min) |
| EDDN lag p50/p90 | 1.8 s / 5.1 s | |

Top schemas: journal/1 4441, fsssignaldiscovered 769, fssbodysignals 606, fssdiscoveryscan 449, dockinggranted 415, **commodity/3 406**, navroute 350, outfitting/2 173, shipyard/2 135.
Uploaders: EDMC (Win+Linux) ~52%, EDDiscovery 19%, EDO Materials Helper 16%.
This was midday UTC on a weekday. Assume evenings and weekends run 1.5 to 3x.

**Market counts** (Ardent `/v2/stats`, EDDN-fed, read today):
- 167,478 markets ever seen and 37.3M price rows. Both include long-dead fleet carriers and settlements.
- 708k stations including 20.8k carriers.
- 10.6k stations and **1.50M price rows updated in the last 24 h**.
- 1.5M / ~160 commodities ≈ **~9 to 10k unique markets per day**, which fits our 228 per 15 min with heavy repeats around popular stations.

**Store size** (latest snapshot per market per commodity, `WITHOUT ROWID` PK `(market_id, name)`):
- Measured ~46 B per row including index.
- 1 day active, ~1.5M rows: **~70 MB**.
- 30-day horizon, ~40k markets × ~110 rows: **~200 to 300 MB**.
- Prune rows older than N days (anomalies only matter while fresh). Optionally store only nonzero buy/sell rows; ~55% of rows are both zero.

## 3. Is processing it a big deal? No

- CPU: 1.97 s of CPU over 900 s = **0.22%** on the Mac. That covers decompress, JSON parse of all schemas, and SQLite upsert plus commit per commodity message.
- RSS: **29 MB**.
- The Deck's Zen 2 is maybe 2 to 3x slower per core, so expect ~0.5 to 1% of one core. That is negligible next to the game.
- Write load: ~0.5 commits/s. WAL mode. Keep `synchronous=NORMAL` and batch commits every 1 to 2 s to be kind to the SSD.
- Network: ~70 kbit/s down, irrelevant.
- The Deck should run the listener, since it is always on while the game runs. It can expose results over the existing Control Room server/API so the Mac sees them too.
- Store design:
  - `market(market_id PK, system, station, station_type, ts, recv_ts, gameversion)`
  - `price(market_id, name, buy, sell, stock, demand, PK(market_id,name)) WITHOUT ROWID`
  - `station(market_id PK, system, dist_ls, max_pad, type, updated)`
  - `system(name PK, address, x, y, z)`
  - On commodity/3: replace that market's rows. EDDN snapshots are complete markets, so delete+insert in one transaction is right. **Ignore messages whose `timestamp` is older than what we hold**, since CAPI and journal uploads can arrive out of order.
- Bootstrapping coords, pads and distance to star (commodity/3 lacks them):
  1. **Passive from EDDN**: `journal/1 Docked` gives pads, `DistFromStarLS`, type and StarPos. `FSDJump`/`Location` give system coords. In 15 min this gave metadata for 204 of the 228 markets seen and coords for 219 of 228. After a day or two it covers nearly every active market.
  2. **Lazy lookup** for misses: Ardent `GET /v2/system/name/{system}/stations` returns `distanceToArrival`, `maxLandingPadSize` (1/2/3), `systemX/Y/Z` and `stationType` (verified). Cache it forever except carriers. EDSM also has a system API.
  3. **Bulk dumps** (checked today via HEAD): too heavy for routine use on the Deck. A one-off bootstrap on the Mac is optional.
     - Spansh `galaxy_stations.json.gz` 4.6 GB, daily. It has system coords, station `landingPads`, `distanceToArrival` and market with `updateTime`, but also every body.
     - Spansh `galaxy_1day.json.gz` 1.1 GB.
     - EDSM `stations.json.gz` 2.9 GB (includes commodities) and `systemsPopulated.json.gz` 532 MB.
  - Recommended: 1 + 2. Skip the dumps.
- Fleet carriers: they move (`CarrierJump`), so their coords must not be cached forever. Filter on `carrierDockingAccess` and probably exclude carriers from round trips by default.

## 4. Computing best round trips

Prototype: `roundtrip.py <db> <cargo> <radius_ly>`. It runs in 0.02 s on the 15-minute DB.

- Pairing: for markets 1 and 2 within radius R (Euclidean on system coords):
  - leg A = max over commodities of `(sell@2 − buy@1) × min(cargo, stock@1, demand@2)`
  - leg B = the same in reverse
  - profit per trip = A + B
  - The legs are independent, so they can be computed separately. One-sided routes fall out naturally, since a leg can be 0.
- Filters:
  - `max_pad >= ship pad`, `dist_ls <= limit`
  - exclude Legacy gameversion, `prohibited` items and carriers (default off)
  - freshness, e.g. both snapshots < 2 h for anomaly mode
  - `min_supply`/`min_demand` (already a concept in Haul v1)
- Scale: the bubble has ~10k active markets, with hundreds to ~1k within 30 ly of each other. A full O(pairs × commodities) scan in Python is tens of seconds. Do it smarter:
  - **Incremental**: on each commodity/3 update for market M, rescore only pairs (M, N) with N within R. A spatial grid with cell = R finds neighbors. ~1k neighbors × ~160-item dict intersect is ~10 to 50 ms per update at 0.5 updates/s. Keep a top-K heap.
  - **Anomaly-first**: keep per commodity a rolling robust baseline (median and percentiles of buy/sell across markets over 24 h).
    - Flag `buy < 0.3 × median_buy` with stock > cargo, or `sell > p99`.
    - On a flag, immediately search the best counter-legs within R and announce via TTS/web.
    - This is what catches a "Silver at 3.4k" event within seconds of the first upload.
- Profit/hr: estimate trip time as `2 × (jumps × ~45 s + supercruise(dist_ls) + dock/undock/market ~150 s)`, where jumps = ceil(dist / ship jump range) and supercruise is ~ 30 s + k·log(dist_ls).
  - Calibrate k and the constants from the existing `.control_room_haul_runs.jsonl` (per-run durations with known routes).
  - Then profit/hr = profit/trip × 3600 / trip_time. Rank by profit/hr rather than per trip, since a 291 ls versus 3,200 ls station or a surface port changes it a lot.
  - Also cap by stock depletion: 81k stock / 700 t ≈ 115 trips here. Demand at the sell side (12k at Payson) is often the real limit. Show "trips until demand exhausted".
- Speed versus Inara:
  - Our listener sees an upload ~2 to 5 s after the uploader opens the market.
  - Ardent shows it at the same second (verified for Chauhan Dock / Kutter Platform).
  - Inara's EDDN ingestion delay was not verifiable (its data page returned 410). Inara also needs someone to run a search, and EDCR's current Inara path scrapes via Playwright on demand.
  - The real win is push. The listener can alert within seconds of the first commander docking at an anomalous station. Polling Inara only finds it when we happen to search and Inara has processed it.
  - Detection still depends on some EDDN user docking there. Popular stations get many snapshots per hour; remote ones may get one a day.

## Caveats / open questions

- One 15-minute midday sample. Run a 24 h capture on the Deck (cheap) to get real peak rates and unique markets per day.
- Out-of-order and stale uploads exist. Always compare the message `timestamp`, not receive time.
- Price anomalies may be in-game events (e.g. colonisation or system state) that end abruptly. Show snapshot age prominently.
- Ardent API usage limits and terms were not checked. Be polite: cache, and only do lazy lookups.
