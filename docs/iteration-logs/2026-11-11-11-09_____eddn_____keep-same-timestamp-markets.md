# Iteration Log

- Area: `eddn`
- Title: `keep-same-timestamp-markets`
- Started: `2026-11-11 11:09`

## Summary

- A market snapshot with the same timestamp as the stored one is now kept, not rewritten. A peer restart resends its recent markets, and the hub used to log those as `written` though nothing changed.

## Changes

- `edap/eddn/store.py`: `_apply_market` skips when the stored `updated_at >= snapshot.timestamp` (was `>`).
- Logs say `already in the DB` instead of `already newer`, in `edap/hub.py` and `edap/eddn/game_markets.py`.
- Tests: a resent equal-timestamp snapshot is kept; the file-change import now writes only the new market.

