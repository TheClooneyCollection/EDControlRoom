# Iteration Log

- Area: `haul`
- Title: `show-buy-and-sell-prices-on-routes-and-haul`
- Started: `2026-11-12 19:17`

## Summary

- Only `/markets` showed buy and sell prices. `/routes` legs and `/haul` route rows now show them too.

## Changes

- `TradeRoute` gains `from_buy_price`, `to_sell_price`, `to_buy_price`, `from_sell_price` (strings like the other route fields). All three payload parsers (`control_room_state.py`, `server/commands.py`, `protocol/data_messages.py`) read them.
- Inara parsing reads `BUY PRICE` / `SELL PRICE`, dropping the `| +margin (pct)` suffix on sell prices. The `from` block comes first, so one sell price means the outbound sell at `to`.
- `/routes` EDDN `trade_route` and `/markets` Best deal `tradeRoute` fill the four fields from their legs.
- `/routes` leg cell: `buy → sell (+margin/t) × tons · supply`. `/haul` rows add a `Buy … / Sell …` line under each station's supply/demand; routes saved before this have no line.
- Prices stay out of `ROUTE_TRANSFER_FIELDS`, like supply and demand.

## Follow-ups

- The TUI route picker detail does not show prices yet.
- Full suite runs about 0.76s for 1166 tests, over the 0.70s budget, with or without this change.
