# Iteration Log

- Area: `control-room`
- Title: `markets-best-deal-to-haul`
- Started: `2026-11-10 18:03`

## Summary

- The `/markets` Best deal panel ranks deals by full-hold profit and offers the top 3 per leg to pick, with supply and demand, and hands the picked round trip to the two-way haul: **Copy route** (JSON for the /haul paste box) or **Open in haul**.

## Changes

- `edap/market_compare.py` sorts deals by `hold_profit` first (hold capped by source stock), then profit per ton. Before, a 178 t gold stock beat a deep commodity on profit per ton and became the best deal.
- `web/markets.js`: each leg shows its top `DEAL_CHOICES = 3` deals with a radio pick (buy, supply, sell, demand, profit/t, full hold); the periodic refresh keeps the picks for the same pair. `tradeRoute` builds the /haul route from the picks in the browser (X is `from`; manual landing off).
- **Open in haul** links to `/haul#route=<json>`. `importLinkedRoute` in `web/haul-ui.js` runs after each hydrate, clears the fragment and goes through `importPastedRoute`, so the route becomes the server's selected route when the page is the active operator.
- `/haul` routine panel: Elapsed was always the session total (falling back to the current run only at 0); it is now labelled Session elapsed, and a second row shows This run (`current_run_elapsed_s`, live from the hydrate), Last run and Avg run (`total_run_elapsed_s / completed_runs`).

## Follow-ups

- Not yet tried in a browser. Station distances and profit per hour are not in `Market.json`, so the linked route leaves them empty.
