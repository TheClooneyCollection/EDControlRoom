# Iteration Log

- Area: `control-room`
- Title: `inara-search-link`
- Started: `2026-11-11 00:16`

## Summary

- Inara searches now round the max route distance up to a whole light year, and the `/haul` page links the search it ran on Inara.

## Changes

- `build_trade_route_query_params` in `edap/inara/trade_routes.py` sends `pi2` as the ceiling of the distance (`17.2` -> `18`, `18.0` -> `18`). Inara truncates `pi2` to an integer, so `17.2` acted as `17` and dropped a `17.05` Ly route. Empty or non-numeric values pass through unchanged. The parsed `pi2` from a pasted Inara URL is not changed.
- `/haul`: an **Open in Inara** link (`#inara-search-link`, new tab, `rel=noopener`) sits next to `#result-count`. A successful `command.search_haul_routes` sets it from `result.query_url`; a new search or a failed one hides it.

## Follow-ups

- The link does not survive a page reload. Search results themselves are not in the hydrate (only the selected route), and `TradeRoutePickerState.presented_query_url` is TUI picker state that the web search never sets, so wiring it would need a new hydrate field.
- Not yet tried in a browser.
