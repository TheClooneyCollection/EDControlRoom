# 0018: Static Trade Routes Website

## Status

Thought experiment (2026-11-14): a proposal for a future EDCR team, not scheduled. Builds on [plan 0017](0017-hosted-market-snapshot.md), the VPS, R2 and Cloudflare setup it describes.

## Why

With a hosted market DB, players can find routes on a public website without running EDCR. A route found there copies into a local `/haul` through the existing Copy / paste route box.

## Decisions (confirmed with the user)

- All static: the VPS generates the data files each hour next to the snapshot, R2 stores them and Cloudflare Pages serves the site. No query API and no compute at request time, so traffic only costs CDN hits.
- Global is the best deals plus filtering. Profit per ton for a round trip (outbound margin + return margin) does not depend on cargo or jump range, so one ranked list serves every player and the page filters it.
- Cargo capacity is a filter, not a ranking input: routes show profit per ton and both stocks, and the page caps the hold by stock when a capacity is given.
- The browser computes distances from system coordinates, jumps from the player's own laden range, and the trip time from the `TimeModel` formula.

## Design

### Data files (per hourly run)

- `stations.json`: per market id the station, system, coordinates, type, `dist_ls`, pad, surface flag, carrier name and access, data age.
- `routes.json`, one candidate table, with rows as station ids, route distance, and per direction the top 3 commodities by margin with buy price, sell price and supply, so a min supply filter falls back to the next commodity instead of dropping the leg:
  - Global: the top few thousand round trips by profit per ton within 250 Ly, unfiltered, so strict filters (S pad, no carriers, high min supply) still leave rows.
  - A short extra list ranked by profit per hour at a common laden range, so same-system and 1-jump routes with a modest margin are not missed.
  - Near: for each station, its best partners by profit per ton within distance caps (20, 50, 100, 250 Ly), so a short-range ship still sees nearby partners.
- `systems-<prefix>.json`: every system the DB knows with coordinates (127,584 systems, 2.2 MB gzip on 2026-11-14), split by name prefix so a lookup downloads a few KB. Systems with a station alone are 12,869 (195 KB gzip).
- The files come from the existing `edcr/eddn/routes.py` code on the VPS, so ranking stays in one implementation.

### Page

- Filters: pad, surface stations, carriers open only, min supply, max station distance, max data age, route distance cap (from jumps × laden range, or Ly), cargo capacity.
- Current system: look up coordinates in the systems files; an unknown system says so and asks for a nearby one.
- Per route: profit per ton per trip, both stocks, jumps, trip time from the published `TimeModel` (editable, kept in localStorage), profit per hour, and per trip and per hour with a capacity given, `<n> Ly away` from the current system.
- Global sorts the filtered Global rows; Near keeps rows whose station A is within the radius, then sorts.
- Show what filters left out (for example `312 routes hidden by min supply`), as the repo rule says.
- Copy gives the route JSON the `/haul` route box imports.

## Build steps

1. Measure: generate the files from a real DB, time and size them, and compare Global and Near against local `/routes` at the same settings.
2. Generator tool and the hourly VPS run after the snapshot upload.
3. Static page on Cloudflare Pages, reusing `web/routes.js` rendering where it fits.
4. Docs: a player doc for the website and the haul status.

## Rejected ideas (with the user's reasons)

- A query API on the VPS behind Cloudflare Tunnel and cache: rejected for all static data, which needs no compute or VPS capacity per visitor.
- Ranking in the browser on the full SQLite snapshot (sql.js, or Pyodide running the Python): rejected for the same reason; it would also mean a JS port of the ranking or a heavy runtime on phones.
- Cloudflare Workers with D1 for queries: Worker CPU limits and D1 write quotas do not fit an hourly reload of 1.5M prices.
- One precomputed top list per parameter combination (pad, cargo bands, jump bands, surface): rejected because profit per ton, trip time and profit per hour all derive in the browser from per-ton margins, stock, distance and the `TimeModel`.
- Picking each leg's commodity by cargo capacity (a high-margin, low-stock commodity against a lower-margin, high-stock one): rejected; show stock and let the page filter.
- Candidate files per laden jump range band: dropped once Global was framed as best deals plus filtering; distance caps cover short-range ships without bands.

## Open points

- How many Global rows and Near partners per station keep the files small but the results matching `/routes`.
- Domain and site name.
- Where the page's published `TimeModel` comes from (defaults, or a fit from journals).

## Validation

- At the same settings, the page's Global and Near top routes match local `/routes`.
- A min supply filter that hides a leg's best commodity falls back to the next one.
- The page works with the VPS off, on the last uploaded files.
