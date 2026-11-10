# Iteration Log

- Area: `haul`
- Title: `eddn-trade-routes-plan`
- Started: `2026-11-10 14:26`

## Summary

- Planned an EDDN-based trade route finder to replace the Inara scrape: [plan 0014](../plans/0014-eddn-trade-routes.md).

## Decisions

- Runs on the Mac, latest snapshot only (no price history), SQLite; Ardent lookups on demand; fleet carriers excluded by default.
- Near view (default) plus a global view of the best routes anywhere.
- Ranked by estimated profit per hour; multi-jump routes are allowed and rank high only when the profit pays for the extra jumps.
- Range presets in laden jumps (1, 2, 4 default) plus wide 100 ly+ presets. Current Panther Mk II laden range computes to 17.19 ly from `Loadout`, matching `max_route_distance_ly = 17.2`.
- Anomaly alerts named "Good Deals / Exceptional Routes", deferred to a later phase.
