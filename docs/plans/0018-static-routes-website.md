# 0018: Static Trade Routes Website

## Status

Proposed (2026-11-13). Not started. Builds on [plan 0017](0017-hosted-market-snapshot.md): the VPS, R2 and Cloudflare setup it describes.

## Why

With a hosted market DB, players can find routes on a public website without running EDCR. A route found there copies into a local `/haul` through the existing Copy / paste route box.

## Decisions (confirmed with the user)

- All static: the VPS generates the data files each hour next to the snapshot, R2 stores them and Cloudflare Pages serves the site. No query API, no compute at request time, so traffic only costs CDN hits.
- No cargo capacity: routes show profit per ton and the seller's stock; the page filters on min supply. Per trip and per hour figures are per ton.
- Laden jump range is picked from fixed bands; the VPS precomputes candidates per band.
- The browser computes distances from system coordinates and the trip time from the `TimeModel` formula, so Near and Global are filters and sorts over static rows.

## Design

### Data files (per hourly run)

- `stations.json`: per market id the station, system, coordinates, type, `dist_ls`, pad, surface flag, carrier name and access, data age.
- `routes-<band>.json` per laden jump range band (for example 10, 15, 20, 25, 30, 40, 50 Ly): candidate round trips A -> B -> A as station ids, route distance, and per direction the top 3 commodities by margin with buy price, sell price and supply, so a min supply filter falls back to the next commodity instead of dropping the leg.
- Candidates: for each station A, its best partners by profit per ton per hour at that band, within each route distance cap the page offers (1, 2 and 4 jumps, 100 and 250 Ly). Partners are kept with no supply filter so the page can apply its own.
- `systems-<prefix>.json`: every system the DB knows with coordinates (127,584 systems, 2.2 MB gzip on 2026-11-13), split by name prefix so a lookup downloads a few KB. Systems with a station alone are 12,869 (195 KB gzip).
- All files go through the existing `edcr/eddn/routes.py` code on the VPS, so ranking stays in one implementation.

### Page

- Inputs: current system, jump band, jumps or Ly cap, pad, surface stations, carriers open only, max station distance, max data age, min supply, Near radius.
- Current system: look up coordinates in the systems files; an unknown system says so and asks for a nearby one (or, later, looks it up from EDSM or Spansh if their APIs allow cross-origin calls).
- Per route: jumps = ceil(distance / band), trip time from the published `TimeModel` (editable on the page, kept in localStorage), profit per ton per trip and per hour, both stocks, `<n> Ly away` from the current system.
- Global: sort all candidates of the band, show the top 100. Near: keep routes whose station A is within the radius, then sort.
- Copy gives the route JSON the `/haul` route box imports.
- Show what filters left out (for example `312 routes hidden by min supply`), as the repo rule says.

## Build steps

1. Measure: generate one band's candidates from a real DB, time it, size it, and compare its Near and Global results against local `/routes` at the same settings.
2. Generator tool and the hourly VPS run after the snapshot upload.
3. Static page on Cloudflare Pages, reusing `web/routes.js` rendering where it fits.
4. Docs: a player doc for the website and the haul status.

## Open points

- The band list and how many partners per station keep the files small but the results matching `/routes`.
- Domain and site name.
- Where the page's published `TimeModel` comes from (defaults, or a fit from the VPS owner's journals).

## Validation

- At a band's exact range, the page's Global and Near top routes match local `/routes` with the same filters (capacity aside).
- A min supply filter that hides a leg's best commodity falls back to the next one.
- The page works with the VPS off, on the last uploaded files.
