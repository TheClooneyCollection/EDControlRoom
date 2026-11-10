# Iteration Log

- Area: `haul`
- Title: `aborted-run-session-profit`
- Started: `2026-11-10 15:00`

## Summary

- Trades from a haul run that was stopped mid-way vanished from the session profit: `start_haul_stats` built new stats from `accumulated_profit` only and dropped `current_run_profit`, and a station 1 sale on a resumed run was discarded. The persisted JSONL rows and the `Today` all-in total already kept them. User decision: realized trades count in the session; profit/hour and expected vs actual stay completed-only.

## Changes

- New `haul_history.abort_run` closes a run as aborted and folds its realized profit into `accumulated_profit`: `current_run_profit` for a clean run, the recorded row profit for a partial (resumed mid-run) row. All aborted closes (stop, new haul over a stale run, clear, restart, resumed run ending) use it; restart adds nothing twice because the saved session profit already includes `current_run_profit`.
- Web Haul v1 connection banner (reconnect) now floats at the bottom of the viewport (bottom-right on desktop, full width on phones) so it stays reachable while scrolled down to the activity log.

## Follow-ups

- None.
