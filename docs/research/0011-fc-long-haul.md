# Fleet Carrier long-distance bulk hauling

Date: 2026-11-28 · M10 · Decision: no feature to build at current prices.

Question: is buying cheap, high-supply commodities, carrying them by Fleet Carrier (FC), then selling far away worthwhile? The best sampled run earns **87.9M Cr/h**, well below the supplied **200–300M Cr/h** benchmark for good two-way hauls.

## Data and selection

Local EDDN market store: `.eddn_markets.sqlite3`, coverage 2026-11-20 through 2026-11-28. These are snapshot estimates, not live trade promises.

| Coverage | Count |
| --- | ---: |
| Systems (all with coordinates) | 446,756 |
| Stations | 64,919 |
| Markets (including 3,718 carriers) | 30,714 |
| Price rows | 2,545,616 |
| Commodities | 548 |

- Require L pad, non-carrier, neither Depot nor ConstructionSite station type, market update within 3 days, and station distance at most 3,000 ls. The scripts also admit unknown station distances. Their printed `<=7d` label is stale; SQL uses 3 days.
- Remove a row if either buy or sell exceeds 3× that commodity's median sell price among eligible rows.
- For each commodity, sample the 10 cheapest positive-price sources with supply ≥5,000 t and the 10 highest positive-price destinations with demand ≥1 t. Require different systems, the distance floor, positive margin and transferable cargo ≥3,000 t. Rank the best sampled pair per commodity by Cr/h; this is not an exhaustive pair search.

| Run | Eligible rows | Rows after outlier filter | Outlier rows removed | Commodities after filter | No qualifying sampled pair | Commodities with a pair |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `fc2.py`, ≥300 Ly | 964,630 | 953,648 | 10,982 | 384 | 265 | 119 |
| `fc2.py`, ≥1,000 Ly | 964,620 | 953,638 | 10,982 | 384 | 280 | 104 |
| `fc3.py`, ≥300 Ly | 965,046 | 954,017 | 11,029 | 384 | 265 | 119 |
| `fc3.py`, ≥1,000 Ly | 965,046 | 954,017 | 11,029 | 384 | 280 | 104 |

- Source outputs: `fc_top300.txt`, `fc_top1000.txt`, `fc3_top300.txt`, `fc3_top1000.txt`; scratch scripts and outputs are not committed. Small row-count differences reflect separate reads of the changing store.
- The output's `no_pair_>=3000t` count groups all pair failures above; it does not distinguish distance, quantity or margin failures. Separate counts for pad, age, station type and distance exclusions were not emitted. Overall coverage has 164 more commodities than the filtered sample, without a per-reason breakdown.

## Time and profit model

| Assumption | Value |
| --- | --- |
| Usable FC cargo | About 19,000 t: 25,000 t maximum minus repair/refuel/rearm, shipyard and outfitting allocation |
| Ferry ship cargo | 1,137 t |
| Ferry round trip | 10 min at either end |
| Full-load ferry work | 17 round trips at each end; 340 min = 5 h 40 min |
| FC jump | 15 min per jump, at most 500 Ly |

For cargo `T = min(19,000, supply, demand)` and distance `D`:

- Minutes = `2 × ceil(T / 1,137) × 10 + ceil(D / 500) × 15`.
- Gross profit = `T × (destination sell − source buy)`; Cr/h = profit divided by hours.
- `fc2.py` used an earlier 20,000 t FC / 700 t ship assumption; the results below use only the corrected `fc3.py` model.

## Best sampled pairs

Top five commodities per distance floor; `M` means million credits. Station names follow `system / station`. All rows carry 19,000 t except the ≥1,000 Ly palladium run (14,487 t). Of 119 and 104 qualifying commodities respectively, 114 and 99 lower-ranked commodities are omitted here.

| Floor | Commodity | Buy at → sell at | Buy → sell (Cr/t) | Margin (Cr/t) | Ly / jumps | Hours | Profit (M) | M/h |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 300 Ly | Palladium | HIP 40900 / Yah's Provision → Brestla / Roed Odegaard Port | 43,810 → 71,192 | 27,382 | 304 / 1 | 5.9 | 520.3 | 87.9 |
| 300 Ly | Gold | HIP 40900 / Yah's Provision → Brestla / Roed Odegaard Port | 41,106 → 67,492 | 26,386 | 304 / 1 | 5.9 | 501.3 | 84.7 |
| 300 Ly | Cryolite | Saxon / Cyning City → Col 285 Sector KN-T d3-46 / Frontier Place | 8,592 → 29,940 | 21,348 | 360 / 1 | 5.9 | 405.6 | 68.6 |
| 300 Ly | Pyrophyllite | Saxon / Cyning City → Col 285 Sector KN-T d3-46 / Frontier Place | 8,410 → 29,098 | 20,688 | 360 / 1 | 5.9 | 393.1 | 66.4 |
| 300 Ly | Bertrandite | Col 285 Sector SU-F c11-9 / Muci Memorial → Col 359 Sector DA-W c3-10 / Temple Landing | 1,683 → 21,649 | 19,966 | 371 / 1 | 5.9 | 379.4 | 64.1 |
| 1,000 Ly | Palladium | Pelican Sector QI-T c3-11 / The Deadstar Foundation: Nebula One → Mehuenomici / Bohr Gateway | 47,172 → 71,073 | 23,901 | 1,936 / 4 | 5.3 | 346.3 | 64.9 |
| 1,000 Ly | Cryolite | Saxon / Cyning City → Bleae Thaa BJ-T d3-28 / May Terminal | 8,592 → 29,940 | 21,348 | 3,251 / 7 | 7.4 | 405.6 | 54.7 |
| 1,000 Ly | Pyrophyllite | Saxon / Cyning City → Bleae Thaa BJ-T d3-28 / May Terminal | 8,410 → 29,098 | 20,688 | 3,251 / 7 | 7.4 | 393.1 | 53.0 |
| 1,000 Ly | CMM Composite | M7 Sector VO-R d4-0 / Gustard Venture → Ocaina / Vinci Ring | 4,929 → 19,994 | 15,065 | 1,050 / 3 | 6.4 | 286.2 | 44.6 |
| 1,000 Ly | Bertrandite | Col 285 Sector SU-F c11-9 / Muci Memorial → NGC 6357 Sector EL-Y d224 / Friend Refinery | 1,683 → 21,649 | 19,966 | 8,047 / 17 | 9.9 | 379.4 | 38.3 |

## Break-even and decision

- Ferrying a full load takes 5 h 40 min; the best pair adds only 15 min in jumps. Distance barely changes the economics over a few jumps because ferrying dominates. This does not hold across the galaxy: 17 jumps add 4 h 15 min.
- Every ton is ferried twice but earns its trading margin once. Before jumps, throughput is about 3,400 t/h (`19,000 / (340 / 60)` ≈3,353). Matching 200–300M Cr/h requires roughly 60–90k Cr/t; about **70k Cr/t** is a useful midrange hurdle, higher once jumps and other costs are counted.
- A separate research check without the outlier filter found **0 of 389 commodities** with margin ≥60k Cr/t and both supply and demand ≥10,000 t. This count comes from the research summary, not the four ranked-output files.
- **Not worth it at the sampled prices. No FC hauling feature will be built.** Recheck only if margins change materially, for example a new colony demand spike.

## Caveats

- Price outliers exist; the median rule is a heuristic and can remove real spikes or retain bad low prices.
- Selling above demand drops the price and was not modelled. Ranked runs cap quantity at reported demand, but quotes and demand can change during the hours of ferrying; prices are held fixed in the calculation.
- Tritium costs and FC repositioning time before/after the cargo run are excluded. The straight-line jump count also assumes suitable intermediate systems. These estimates are optimistic gross returns.
