# Iteration Log

- Area: `control-room`
- Title: `home-set-current-system`
- Started: `2026-06-18 11:19`

## Summary

- `home set` now uses the current detected ship system when no explicit system name is provided, so commanders can save home with one short command after bootstrap/live sync has populated the current location.

## Changes

- Updated the `home` command parser so both `home set <system>` and bare `home set` share the same config-write path.
- Added a specific operator-facing message for the case where Control Room still does not know the current system, instead of falling back to generic usage text.
- Added dispatch tests for the inferred-current-system path and the unknown-current-system failure path, and refreshed the user-facing docs/help text to mention the shortcut.
- Verified with `uv run python3 -m unittest discover -s tests` (`413` tests, `0.232s`), then ran `UV_CACHE_DIR=/private/tmp/uv-cache uv run python3 tools/report_test_timing.py --top 10 --sort slowest` per repo policy (`0.222s` total in the timing report).

## Follow-ups

- Live-check that `home set` picks the expected system after bootstrap on a real session, especially when Control Room inferred location from `Status.json` or market state rather than a fresh jump/location journal event.
