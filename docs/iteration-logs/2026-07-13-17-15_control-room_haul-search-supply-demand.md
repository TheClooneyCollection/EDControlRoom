# Iteration Log

- Area: `control-room`
- Title: `haul-search-supply-demand`
- Started: `2026-07-13 17:15`

## Summary

- Surface Inara supply/demand per station in the web haul search results and let operators filter by them.

## Changes

- `edap/inara/trade_routes.py`: added `from_supply`, `from_demand`, `to_supply`, `to_demand` to `TradeRoute` and populated them in `_row_to_route()` via `_extract_repeated_field_values` (first SUPPLY/DEMAND = source station, second = target station).
- `edap/control_room_state.py`: `_trade_route_from_payload` reads the new keys so persisted trade routes round-trip supply/demand.
- `web/haul-ui.js`: `routeFromApi` / `tradeRoutePayload` carry the new fields; `renderRows` adds a `Sup n / Dem n` subline under each station cell; `WEB_DEFAULTS` gains `minSupply` / `minDemand`; search body sends `min_supply` / `min_demand`.
- `web/haul-v1.html`: new "Min supply" / "Min demand" field row in the search form.
- `edap/control_room/server/app.py`: `_haul_search_query_params` forwards `min_supply` / `min_demand`; these persist via the existing `_save_haul_search_defaults` call so they land in `haul_search.toml`.
- `edap/control_room/dependencies.py`: exposes `minSupply` / `minDemand` in the web defaults payload, seeded from the loaded haul search config.
- `tests/test_inara_trade_routes.py`: extended layout test to assert the four new fields.

## Follow-ups

- `web/multi-haul.*` does not display Inara route boxes; leave supply/demand exposure there for a later pass if the multi-leg planner starts surfacing per-station stock.
</content>
</invoke>