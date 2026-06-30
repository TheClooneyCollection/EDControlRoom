# Iteration Log

- Area: `control-room`
- Title: `fix-connect-target-wiring`
- Started: `2026-06-30 22:28`

## Summary

- Fixed connect-mode startup after the live CLI path hit stale target/runtime API usage.

## Changes

- Use `ObserverServerTarget.websocket_url` and call `build_remote_observer_websocket_connect_info()` with its current keyword-only signature.
- Queue `--claim-operator` through `RemoteObserverBackend.request_active_operator()` after backend construction.
- Align connect runtime context creation with the current `load_config_with_fallback()` return shape.
- Added a regression test that uses the real websocket connect-info builder instead of mocking away the failing call.

## Follow-ups

- Re-run live `uv run control_room.py connect ...` against the server after this commit.
