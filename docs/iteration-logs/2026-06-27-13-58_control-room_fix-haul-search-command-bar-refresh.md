# Iteration Log

- Area: `control-room`
- Title: `fix-haul-search-command-bar-refresh`
- Started: `2026-06-27 13:58`

## Summary

- Fixed a Control Room prompt-refresh regression where active command-bar prefills could snap back to stale or blank text during periodic snapshot refreshes, making `haul search` editing unusable in local mode.

## Changes

- Updated prompt-state snapshot serialization to prefer the live `#cmd` widget placeholder/value whenever prompt-owned prefill is active, so periodic UI refreshes keep the operator's in-progress text instead of replaying stale prompt-state fields.
- Added protocol coverage proving snapshot generation preserves live command-bar edits during an active prefill session.
- Re-ran the full `uv run python3 -m unittest discover -s tests` suite and the required slow-test timing report because suite runtime stayed above the repo's `0.3s` target.

## Follow-ups

- Live-check `haul search` editing in the real local TUI to confirm the command bar now stays stable while the periodic status refresh loop is running.
