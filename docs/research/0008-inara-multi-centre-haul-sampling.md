# Inara Multi-Centre Haul Sampling

Date: 2026-11-10

Status: research only, no implementation decided.

Related: [0008](0008-inara-multi-centre-haul-sampling.md), [0009](0009-ardent-api-haul-source.md), [0010](0010-eddn-listener-haul-routes.md)

Note: Scratch probes (`probe.py`, `probe2.py`) and raw `out/` captures were not kept in the repo.

Date: 2026-11-10 (live searches about 13:40-13:50 UTC). Investigation only, nothing in the repo changed.
Raw data: `out/*.json` (parsed routes) and `out/*.json.html` (full page HTML) next to this file. The scripts used are `probe.py` and `probe2.py`, also next to this file.

## TL;DR

- **With the repo default `order_by = best_profit_per_hour_estimate` (`pi1=4`), the centre system makes no difference.** Sol, Diaguandri (about 130 Ly away) and Maia (Pleiades, about 383 Ly away) returned the **same 50 routes in the same order with the same profit/hr**. 49 of 50 rows matched exactly, and the one difference was a row whose price refreshed between calls. `ps1` only fills in the "Distance" column. Inara ranks across the whole galaxy, or at least across more than 470 Ly. So sampling from several centres while ordering by profit/hr **gives no new routes at all**.
- The one ordering where the centre matters is `order_by = distance` (`pi1=3`). It returns the 50 routes whose **source system** is nearest to `ps1`. Around Sol that reaches only **18 Ly**, because the core is dense. Covering the bubble that way takes hundreds of searches, which is not viable.
- Results are capped at **50 rows**, with no pagination. The form has no "max distance from system" filter.
- Recommendation: drop spatial centre sampling for "best in the bubble right now". Use **1 global profit/hr search**. If more than the top 50 is wanted, partition with **disjoint filters** such as source-station Power (`pi14`). Optionally add **1 distance-ordered search at the player's current system** for "best near me". See §3.

## 1. How far one search reaches (4 real searches)

Every search used the repo defaults (`defaults/haul_search.toml`: 460 t, max route 500 Ly, price age 8 h, L pad, no surface, supply/demand ≥ 5000, round trips on). I called `search_trade_routes` directly for the first one. The other three used a copy of `fetch_trade_routes` that also saved the HTML, with the same profile and the same headless Chromium. Nothing wrote `haul_search.toml`.

| # | ps1 | order | rows | distance_from_system min / median / max | top destinations |
|---|-----|-------|------|------------------------------------------|------------------|
| 1 | Sol | profit/hr | 50 | 9 / 80 / 192 Ly | Beregovoi Colony 24, Braddocks Hide 12, Al-Khujandi 9, Pribylov 4 |
| 2 | Diaguandri | profit/hr | 50 | 110 / 170 / 253 Ly | same |
| 3 | Maia | profit/hr | 50 | 313 / 399 / 471 Ly | same |
| 4 | Sol | distance | 50 | 0 / 11 / 18 Ly | spread out: Braddocks 8, Beregovoi 7, Renfroe 6, Evanc 6 |

- Overlap: Sol∩Diaguandri = 49/50, Sol∩Maia = 49/50, Sol(profit)∩Sol(distance) = 2/50. Across all 4 searches there are 99 unique rows.
- So the earlier observation that "a search near Sol returned routes about 53-185 Ly away" was really the global top 50 seen from Sol, not a radius.
- `distance_from_system` is the distance from `ps1` to the **source** system only. The destination can be another 15-200 Ly beyond it.
- The top 50 is heavily concentrated: 46 unique station pairs, and about 50% of rows sell into a single station (ORISHPUCHO / Beregovoi Colony, which pays about 35k Cr for Bauxite). One market anomaly can fill most of the 50 slots.
- How the fetch works: Playwright `launch_persistent_context` on `artifacts/playwright/inara-profile`, headless by default (`show_browser=False`). It loads the page, polls `div.mainblock.traderoutebox` and parses `innerText`. If it detects the "Access check required" interstitial while headless, it raises. Each request is one full page load of about 360 KB of HTML, plus assets.
- Latency, measured: about **0.9-1.2 s end to end** per search (Chromium launch 0.2-0.5 s, `goto` about 0.5 s, rows ready in under 0.1 s). There was no access check on any of the 4 requests, which were about 1-5 minutes apart. The cost is dominated by any politeness delay we add, not by the fetch.
- The form's parameters are `ps1, pi1, pi2, pi3, pi4, pi5, pi7, pi8, pi9, pi10, pi12, pi14, pi15` (plus `pa4`, `pa5`). `pi1` options: 0 best profit, 1 last update, 2 route distance, 3 distance, 4 best profit/hr. There is **no** max-distance-from-system parameter.
- Not tested, because it was out of budget: whether a `ps1` far outside the bubble, such as Colonia, still gets the bubble's top 50 or a capped radius. I also did not verify whether `pi14`/`pi15` Power filters partition the results cleanly.

## 2. Rate limits, ToS, bot detection

- **Inara API** (`https://inara.cz/inapi/v1/`) covers commander data only. The dev guide says: *"It does not include markets, minor faction influences, star systems, stations, or similar outputs."* Its events are commander profile, ranks, credits, inventory, ships, travel log, missions, combat, and community goals. There is **no market or trade-route endpoint**. API keys need whitelisting, and the guide warns: *"excessive amount of requests in a short time may lead to the API key invalidation"*. No numeric limit is given.
- **Website ToS** (`https://inara.cz/elite/policies/`): *"You must also not use automated means (such as bots, scrapers, or crawlers) to access or collect content from the Service in a way that violates these Terms or unreasonably interferes with the Service, without our permission."* Inara also *"may monitor activity... restrict access"*. Low-volume, user-triggered searches are a grey area that is arguably fine. Bulk sampling loops are the case this clause targets. For anything scheduled, or more than about 10 searches per run, asking Inara (Artie) for permission is the clean path.
- **robots.txt**: `/elite/market-traderoutes/` is **not** disallowed. `/elite/market-traderoutes-search/` **is** disallowed, so avoid that page.
- **Bot protection**: Inara has an "Access check required / Confirm and continue" interstitial, and the scraper already handles it (it fails when headless, and waits when the browser is visible). The persistent profile keeps the cleared state. No numeric rate limit is published. Suggested policy: at least 30 s between searches, at most about 15 per run, one run per hour at most, and stop the whole batch on the first access check.
- `/elite/faq/` returns 410 Gone.

## 3. Centre selection

### Why spatial centres don't help for "best profit/hr"
Profit/hr ordering ignores `ps1`, so N centres return N copies of the same 50 rows. The only spatially local mode is distance ordering, and its reach is the radius at which 50 qualifying routes accumulate. Measured: **about 18 Ly at Sol**. The radius grows towards the sparse edges, maybe 40-80 Ly, but that is a guess and was not measured. Rough cost to cover the core bubble (about a 150 Ly radius) with balls of 18-40 Ly is 50-600 searches. At 30 s spacing that is 25 minutes to 5 hours, and it would collide with the ToS clause. Not recommended.

### Recommended: global search plus disjoint filter partitions plus an optional "near me"
1. **Global top**: 1 search, `order_by=best_profit_per_hour_estimate`, `ps1` = the player's current system from the journal `FSDJump`/`Location` `StarSystem`, so the Distance column means "from me".
2. **Breadth beyond the top 50** (optional, only when the top 50 is dominated by a few destinations): repeat with **source-station Power `pi14`** set to each of the 12 powers plus `-1` (None). These are disjoint by construction, so each partition contributes its own top 50. That is up to 13 searches, about 7 minutes at 30 s spacing, and roughly 650 rows before dedup. Verify first, with 2 searches, that `pi14=<power>` really filters the source station and returns different rows. A cheaper alternative that is nested rather than disjoint: `max_route_distance_ly` in {20, 40, 80} surfaces short-hop routes that are hidden under the long-haul anomalies. That is 3 searches.
3. **Near me**: 1 search with `order_by=distance`, `ps1` = current system, then re-rank locally by profit/hr. This gives "best within about 20-50 Ly" without depending on the global anomaly.

Typical run: 2 searches (global + near me) in about 35 s. Full sweep: 2 + 13 = 15 searches in about 8 minutes.

### If spatial sampling is still wanted (distance-ordered mode)
Use **adaptive greedy set cover**, not a fixed grid or k-means:
- Coordinates: journal `StarPos` for visited systems (free, local). For populated systems use the EDSM API (`/api-v1/system?showCoordinates=1`, `/api-v1/sphere-systems`), which works from curl and limits in headers. Or use the dumps: EDSM `systemsPopulated.json.gz` is **532 MB** and Spansh `galaxy_populated.json.gz` is **4.66 GB**, both refreshed daily. Download once, filter to systems with large-pad stations, and cache the coordinates as a small local file. Spansh also has `galaxy_stations.json.gz` (4.6 GB), which includes markets, so it could replace Inara entirely for offline route computation. That is a bigger project.
- Algorithm: weight each populated system by its large-pad station count. Start at the heaviest uncovered system. Search, set its reach r = max `distance_from_system` of the 50 rows, and mark all systems within r as covered. Repeat at the heaviest uncovered system and stop at a search budget. This adapts automatically to dense cores, where r is about 18 Ly, and sparse fringes, where r is larger. Poisson-disc sampling with a fixed spacing wastes searches because the reach varies by about 3x or more. k-means ignores reach entirely.
- Budget: cap at about 10-15 searches per run. That covers the densest station clusters, not the whole bubble.

## 4. Dedup, merge and ranking

- **Station identity**: use Inara market IDs from `url_links[0]` and `url_links[1]` (`/elite/station-market/<id>/`). They are stable, unlike names, and `from_system` arrives uppercased.
- **Round-trip key**: `frozenset({from_market_id, to_market_id})`. A→B buying X and returning with Y is the same round trip as B→A buying Y and returning with X. When merging the reverse direction, swap the source and target commodities so they line up.
- **Same pair with different commodities** (seen: PARTA→ORISHPUCHO with Bauxite at 73.2M/hr vs Rutile at 45.2M/hr; V886 Centauri twice): keep the best profit/hr as the primary row and attach the others as `alternatives`. They are useful when supply runs out.
- **The same row from several searches**: keep the one with the freshest `updated` text, which converts as "N minutes/hours ago" relative to `searched_at`. Recompute distance from the player's system rather than trusting each search's `distance_from_system`, because it is relative to that search's `ps1`. Store `ps1` alongside it, or recompute from coordinates.
- **Ranking**: parse `profit_per_hour` to an int and strip the `"+ BONUS "` prefix. Bonus rows have target demand "Unlimited/0" and are likely construction or colonisation sites with special pricing, so flag them instead of ranking them blindly. Primary sort is profit/hr descending. Tie-breaks are fresher `updated`, then lower `route_distance`. Optionally:
  - Use a **diversity cap** of at most 2-3 round trips per destination station. Otherwise one anomaly (Beregovoi Colony) fills the list.
  - Use a **capacity check**: min(supply, demand) on both legs ≥ the cargo capacity × the planned number of loops. Supply and demand strings carry private-use glyphs (``) that need stripping before `int()`.
  - Use **staleness**: drop or flag anything older than `max_price_age_hours` at merge time.
