# Iteration Log

- Area: `haul`
- Title: `configurable-route-time-model`
- Started: `2026-11-13 17:49`

## Summary

- Checked why Inara's Scortia Hub (AD Leonis) ↔ Ashby City (Luyten's Star) bauxite / military grade fabrics route seemed missing from `/routes`. The DB had both markets with Inara's exact prices, and the route ranked 7th with the same 54,620,343 Cr per trip. It was hidden only by the Near 1/2 jump presets, because the origin radius equals `max_route_ly` and Scortia Hub was 56 Ly from the current system.
- Profit per hour differs from Inara's only through trip time: ours is 930s, while Inara implies about 773s (211M vs 254M Cr/h).
- The trip `TimeModel` can now be set from config, so it can be tuned without a code change.

## Changes

- `edcr/config.py`: `EddnConfig.time_model` is read from `[eddn.time_model]`. Any `TimeModel` field can be overridden on its own; unknown keys, negative values and non-numbers raise `ConfigError`. Defaults are listed in `defaults/eddn.toml`.
- `build_observer_server_app(time_model=...)` passes it to `/api/eddn-routes` and Best deal; `serve.py` passes `config.eddn.time_model`. On a peer, routes still come from the hub's model.
- `docs/user/trade-routes.md`: notes on the Near range with the 1/2 jump presets and on trip time vs Inara, plus the `[eddn.time_model]` settings. `config.example.toml` shows the section.

## Follow-ups

- Idea: fit `TimeModel` from a recent window of journal legs (`Undocked` → `Docked`, jump count, `DistFromStarLS`, docked time), per current ship, falling back to config when there are too few legs.
- Idea: decouple the Near origin radius from the route length so short routes farther away show with the 1/2 jump presets.
- The full suite was already over the 0.0006 s/test budget before this change (0.707 to 0.729s for 1172 tests).
