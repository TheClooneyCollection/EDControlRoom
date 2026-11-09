# Iteration Log

- Area: `control-room`
- Title: `mobile-route-cards`
- Started: `2026-11-09 19:37`

## Summary

- On phone width the `/haul` route results cards showed the wrong labels: CARGO next to the profit, STATION 1 next to the commodity, and the station/system sub-lines fell into the label column.

## Changes

- `web/haul-ui.css`: mobile card labels now come from `content: attr(data-label)` instead of hardcoded `nth-child` labels; every child of a cell sits in the value column (`grid-column: 2`), so multi-line station and supply/demand cells stack correctly.
- `web/haul-ui.js`: each route row cell carries a `data-label` matching its header. `web/route-compare.js` copies labels from its table's `thead` so the comparison tables get the same card layout.
- Test `test_haul_route_cards_label_every_column_like_the_table_header` keeps the row labels in sync with the `haul-v1.html` headers.
- Verified with Playwright at 390x844 against a local preview `serve`.

## Follow-ups

- Route Comparison tables on mobile were not screenshotted with real data.
