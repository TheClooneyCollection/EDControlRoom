# Ardent Insight API as a Haul Source

Date: 2026-11-10

Status: research only, no implementation decided.

Related: [0008](0008-inara-multi-centre-haul-sampling.md), [0009](0009-ardent-api-haul-source.md), [0010](0010-eddn-listener-haul-routes.md)

Note: The PoC script (`ardent_round_trips.py`) and its output were scratch files and were not kept in the repo.

Checked against Ardent API v6.4.1 (`ardent-api-version` header). I read the docs and source in
github.com/iaincollins/ardent-api (README, `router/api/**`, `lib/consts.js`). I sent about 22 live requests.

## TL;DR

- The API is free and anonymous, with no enforced rate limit. It is JSON over plain GETs, built on EDDN data. Each row has an exact
  price, raw stock or demand, and an `updatedAt` timestamp per commodity row. Base URL:
  `https://api.ardent-insight.com/v2` (`api.ardent-industry.com` also answers).
- Ardent does not rank routes. You get per-commodity order books (best 1000 buyers/sellers within ≤500 ly of a
  system). You pair them up yourself. For two-way hauls this is easy: the PoC needs 2 requests per commodity,
  about 30 s total with polite spacing, and finds the same kind of Silver⇄Bertrandite loops Inara shows.
- The server does not filter on pad size, station Ls or surface/orbital. Every row carries
  `maxLandingPadSize`, `distanceToArrival` and `stationType`, so filter on the client.
- Running every few minutes is fine, especially through the 5-minute CDN cache. For heavier use, they publish DB dumps
  and the stack is open source (AGPL-3.0) to self-host.

## 1. Relevant endpoints (verified unless marked "source only")

All accept `/system/name/{name}` or `/system/address/{systemAddress}` (use the address to disambiguate).

| Purpose | URL | Params |
|---|---|---|
| System + coords | `/v2/system/name/LHS%20493` | none. Returns `systemAddress, systemX/Y/Z` |
| Nearby systems | `/v2/system/name/{s}/nearby` (source only) | `maxDistance` ly (default 100, max 500), ≤1000 results |
| **Nearby sellers of X (buy here)** | `/v2/system/name/{s}/commodity/name/{c}/nearby/exports` | `maxDistance` (≤500), `minVolume` (stock ≥), `maxPrice`, `fleetCarriers` (true/false/unset), `maxDaysAgo`, `sort=price\|distance` (undocumented). ≤1000 rows, cheapest first |
| **Nearby buyers of X (sell here)** | `/v2/system/name/{s}/commodity/name/{c}/nearby/imports` | `maxDistance`, `minVolume` (demand ≥, **demand 0 = "infinite", always passes**), `minPrice`, `fleetCarriers`, `maxDaysAgo`, `sort`. ≤1000 rows, highest price first |
| Galaxy-wide best sellers/buyers | `/v2/commodity/name/{c}/exports`, `/imports` | `minVolume`, `maxPrice`/`minPrice`, `fleetCarriers`, `maxDaysAgo`, plus undocumented `systemName`/`systemAddress` + `maxDistance` (≤1000 ly). **Only 100 rows** |
| Orders in one system | `/v2/system/name/{s}/commodity/name/{c}` | `maxDaysAgo`. **Use this for the origin system: `nearby/*` excludes the origin system itself** (`s.systemAddress != @systemAddress`) |
| All orders in a system | `/v2/system/name/{s}/commodities[/imports\|/exports]` | same filters as above |
| **Full market of one station** | `/v2/market/{marketId}/commodities` | none. Verified: 394 rows for Humboldt Hub, but no station metadata (pad/Ls), which comes from the nearby rows or `/system/name/{s}/stations` |
| One commodity at one market | `/v2/market/{marketId}/commodity/name/{c}` | none |
| Stations in system | `/v2/system/name/{s}/stations` (source only) | none |
| Commodity summary | `/v2/commodities`, `/v2/commodity/name/{c}` | daily cached report (min/max/avg, total stock/demand) |

Row shape from the nearby endpoints (verified):
```
commodityName, marketId, stationName, stationType (Coriolis/Orbis/Ocellus/Outpost/CraterOutpost/CraterPort/FleetCarrier/...),
distanceToArrival (Ls, float), maxLandingPadSize (1/2/3), bodyName, systemAddress, systemName, systemX/Y/Z,
buyPrice, sellPrice, stock, stockBracket, demand, demandBracket, meanPrice, updatedAt (ISO, per row), distance (ly from origin, rounded)
```
Commodity names are lowercase internal names (`silver`, `bertrandite`, `imperialslaves`, `lowtemperaturediamond`).

Docs vs code mismatch: README says `maxDaysAgo` defaults to 30. The code (`DEFAULT_MAX_RESULTS_AGE`) uses **90**. Always pass it.

## 2. Limits, auth, caching, terms, freshness

- **Auth:** none. All routes are anonymous.
- **Rate limits:** README says "does not currently enforce any rate limits … respectful use is appreciated. For a very high
  number of queries … run locally. Full database dumps at ardent-insight.com/downloads."
- **Caching:** every response has `cache-control: public, max-age=60, s-maxage=300, stale-while-revalidate=300,
  stale-if-error=86400` behind Caddy. Data seen through a shared cache can be up to about 5 min stale. Polling more often
  than every 1 to 5 min gains nothing.
- **Terms:** no ToS page found in the API docs. Code is AGPL-3.0, which only matters if we vendor or modify their code, not
  for calling the API. Data comes from EDDN (a public CC0-style community feed). Send an identifying `User-Agent`.
- **Freshness:** depends on EDDN uploads. The collector writes each EDDN market message as it arrives, so a row can be
  minutes old (I saw `updatedAt` 2 min before my request) or days old. In the LHS 493 sample the top candidates were
  1 to 16 h old. Stats claim about 560k trade updates per 24 h. Filter with `maxDaysAgo` (whole days only, by `updatedAtDay`)
  and then client-side on `updatedAt` hours.
- **Automated tool every few minutes:** fine. One refresh is about 2 × N_commodities requests (16 for 8 commodities), which
  is negligible load. Add caching, a UA, about 1 s spacing, and back off on errors.

## 3. Query plan for best round trips

Goal: station pair (S1, S2) maximising `margin(A: S1→S2) + margin(B: S2→S1)`, where each station is large pad, ≤1000 Ls,
supply/demand ≥5000.

**Radius plan (implemented in the PoC):**
1. `GET /system/name/{origin}`, optional, to resolve the address.
2. For each of N candidate commodities: `nearby/exports` and `nearby/imports` with `maxDistance=R`, `minVolume=5000`,
   `fleetCarriers=false`, `maxDaysAgo=1..2`. That is **2N requests**.
3. Optionally `GET /system/name/{origin}/commodity/name/{c}` per commodity to include the origin system (N more), or
   `/system/name/{origin}/commodities` once (1 request) for all of them.
4. Client side: filter pad 3, Ls ≤1000, exclude surface/carrier types and old rows. Index by `marketId` into
   `{buy: {c: row}, sell: {c: row}}`. For each unordered pair, take the best A for S1→S2 and the best B for S2→S1. Rank.
5. Optional refinement: for the top K pairs, `GET /market/{marketId}/commodities` on each end (≤2K requests). This finds the
   real best B among *all* commodities, not just the N you queried, and confirms timestamps.

Typical cost: 8 commodities → 16 requests, plus about 10 for refinement. That takes about 30 s with polite spacing,
and well under 1 s of actual server time per request.

**Bubble-wide:** `nearby/*` caps at 500 ly and 1000 rows, and global `/commodity/name/{c}/exports|imports` returns only the
best 100 rows (optionally around a system ≤1000 ly). For bubble-wide pairs use several origins (tiles), or download the dump
and run the pairing locally. Since pair margin is dominated by A and B prices, the global top-100 lists for 10 to 15
high-value commodities (20 to 30 requests) also give a decent bubble-wide shortlist. Station pairs still need to be within
jump range, so the radius approach is the practical one.

**Profit/hr:** Ardent has no travel time. Estimate it ourselves from `systemX/Y/Z` (leg ly → jumps given our laden jump
range), `distanceToArrival` (supercruise time), and fixed dock/undock and market overheads. All of these inputs are in the rows.

### Ardent vs Inara (our current scraper)

| | Ardent | Inara trade routes page |
|---|---|---|
| Access | Public JSON API, no auth, no limits | HTML scrape via Playwright with a browser profile, fragile and against the grain of the site |
| Prices | Exact buy/sell, raw `stock`/`demand` plus brackets, per-row `updatedAt` | Rounded or displayed values, coarse "updated x ago" |
| Route ranking | **None**, so we pair client side | Yes, ranked round trips with profit/trip, distance, and filters for pad, Ls, surface, supply/demand, age |
| Filters server-side | distance, min volume, price, carriers, days-ago | pad, Ls, surface, powerplay, min supply/demand, etc. |
| Coverage of commodities | Only those you query (or full market per station) | Inara searches all commodities for you |
| Coords | Yes, galaxy XYZ for every row | System names only |
| Travel time | No | Distance only, no time either |

Ardent's advantages are machine-readable, exact, timestamped data with coordinates and stable URLs, and refreshing it is cheap.
Its gaps are that we own the pairing logic, there are no server-side pad/Ls/surface filters, the origin system is excluded
from `nearby`, and it has the same EDDN freshness limits as Inara (both get their data from players uploading).

## 4. Proof of concept

Script: `ardent_round_trips.py`
(stdlib only. Run as `uv run python3 ardent_round_trips.py "LHS 493" 40`. It caches raw responses in `raw_poc/` beside it.)
Output: `poc_output.txt`

Run settings: radius 40 ly around LHS 493. Commodities: silver, gold, palladium, bertrandite, indite, gallite, cobalt, tritium.
Filters: large pad, ≤1000 Ls, no surface or carriers, `maxDaysAgo=2`, stock/demand ≥5000. Result: 16 requests, 38 candidate stations,
250 profitable round trips. Top results at 1137 t:

```
22.94 M cr/round trip  Thanatos Minor / Tetrian (226 Ls)  <->  Humboldt Hub / Chelgit (6 Ls), leg 62 ly
   silver      33,563 -> 48,813 = 15,250 cr/t (17.34 M)   stock 7,033 (!)  ages 15-16 h
   bertrandite 16,444 -> 21,370 =  4,926 cr/t ( 5.60 M)
22.54 M  Coye Orbital / LFT 78 (12 Ls) <-> Humboldt Hub / Chelgit (6 Ls), leg 50.5 ly   silver + bertrandite
22.44 M  Tryggvason Orbital / Zeaex (321 Ls) <-> Kregel/Chilton / Kutkha (222-328 Ls), leg 36.4 ly  (fresh: 1-2 h)
```
Silver out and bertrandite back dominates every top pair. Profit per trip is nearly flat across pairs (about 22.3 to 22.9 M), so
distance (leg ly, Ls) and data age should drive the choice. That is exactly the travel-time weighting we would add.

PoC caveats: the A/B search only covers the 8 queried commodities. It does not include the origin system. It does not
account for stock < 1137 t at either end (`stock`/`demand` are in the rows, so this is easy to add). Its distance is from the
origin, not between the pair (the leg ly is computed and printed).

Also verified: `/v2/market/3225948672/commodities` (Humboldt Hub) returns the full market. Top buys there: bertrandite,
imperialslaves, gallite, indite. Top sells: osmium, palladium, tritium, silver. This is the refinement step for pairs.

## Recommendation

Ardent works well as a second source, and probably as a better primary source for the round-trip search. Implement an
`ArdentHaulSource` that runs the radius plan plus market refinement, does the pairing and travel-time ranking locally, and
keeps Inara as a cross-check. Watch for the README/code default mismatch (`maxDaysAgo` 90), the exclusion of the origin system,
and the lack of pad/Ls filters.
