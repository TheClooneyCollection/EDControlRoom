# Iteration Log

- Area: `control-room`
- Title: `haul-web-ship-defaults`
- Started: `2026-07-05 21:52`

## Summary

- Defaulted the web haul planner inputs from current ship hydrate data where available.

## Changes

- Added `max_jump_range_ly` to the ship state/read-model path from journal `Loadout.MaxJumpRange`.
- Web `/haul` and `/multi-haul` now default starting capital from current credits, cargo capacity from current hold capacity, hop distance from hydrated jump range, and the large-pad checkbox from known ship type.
- Two-way web search payload now includes the Spansh-style capital, hop, hops, market-age, and route-filter fields for future backend support.

## Follow-ups

- The UI accepts future `ship.laden_jump_range_ly` / `ship.jump_range_ly` hydrate fields, but today the backend only provides journal `MaxJumpRange`.
- Pad-size inference is a client-side known-ship map; unknown ship types keep the conservative large-pad default.
