# Iteration Log

- Area: `haul`
- Title: `cheapest-markets-plan`
- Started: `2026-11-27 17:30`

## Summary

- Designed M7, a `/cheapest` page listing the cheapest markets for one commodity near a reference system: [plan 0022](../plans/0022-cheapest-markets.md). Nothing built.

## Changes

- Spansh station search sorts by price with `{"market_buy_price":[{"name":"<Commodity>","direction":"asc"}]}`; `market_sell_price` sorts by the station's buy-from-you price, which is why the first guess looked broken. `distance`, `market_updated_at`, `has_large_pad` and a `type` allow-list filter server-side; `type` with `invert` is ignored.
- The hub EDDN store already answers the question: 5536 stations sold Tritium in the last 7 days, and its cheapest station within 200 ly of Adach matched Spansh's.
- Carrier prices are often fake (2565 cr, millions), and many stations list supply under 50.
- User decisions: hub first with Spansh filling in, carriers hidden by default with a count, defaults from the viewed ship (pad, cargo, current system), 7 days, 100 ly, new `/cheapest` page.

## Follow-ups

- Build slices A to D of plan 0022. A ship-type to pad-size table is new in `edcr/ship_types.py`.
