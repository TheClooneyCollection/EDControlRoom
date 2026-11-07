# Iteration Log

- Area: `haul`
- Title: `journal-trade-ledger`
- Started: `2026-11-07 11:14`

## Summary

- Step 3 of haul stats persistence adds a read-only Elite journal trade ledger to `stats` and `tools/haul_stats.py`. It covers manual trading and periods from before run tracking existed. It never creates run rows.

## Changes

- `edap/journal_trade_ledger.journal_trade_ledger(journal_dir, since, until)` returns a frozen, asdict-able `JournalTradeLedger`.
  - **Files scanned:** journal files whose UTC filename stamp falls inside the window, plus the last file that started before it.
  - **Event filtering:** events are filtered by `timestamp`, and torn lines are skipped.
  - **Station attribution:** comes from `Docked`/`Location` `MarketID`.
  - **Totals:** buy and sell counts, cost, revenue, trade profit, and `sell_margin` (`TotalSale - AvgPricePaid*Count`, `None` if any basis is missing), with per-commodity and per-station breakdowns.
  - **Other flows:** module, repair, refuel, mission, voucher, fines and rebuy totals.
- **Balance change** is the difference between observed snapshots, so it is approximate:
  - The start is the last `LoadGame.Credits` at or before the window start, else the first one after it.
  - The end is the latest `LoadGame` or a `Status.json` `Balance` not after `until`.
  - If a session was already running at the window start, money made between that `LoadGame` and the window start is counted in.
- **Output:** `stats` and the CLI render an `All trading (journal)` block, and the CLI JSON gains a `journal` field.
  - The control room reuses its resolved `_journal_dir`. The CLI uses the runtime path resolution, or `--journal-dir`.
  - A missing journal directory shows one line and does not fail.
- **Smoke test** against the real journals with `week`: 52 buys / 51 sells, trade profit 842.0M, observed balance change 841.7M. This matches the earlier hand count of 620M through 2026-11-06 plus today's trading.

## Follow-ups

- Step 4: `/api/haul-stats`, a web History panel, and a one-line TUI summary.
- Coverage reports the first event of the preceding file, which can be weeks before the window when there was a play gap.
