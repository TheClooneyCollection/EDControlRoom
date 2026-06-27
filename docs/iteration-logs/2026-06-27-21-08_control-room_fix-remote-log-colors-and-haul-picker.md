# Iteration Log

- Area: `control-room`
- Title: `fix-remote-log-colors-and-haul-picker`
- Started: `2026-06-27 21:08`

## Summary

- Restored Rich activity-log colors for protocol-streamed observer sessions and fixed the remote haul-results picker so completed searches still open the modal when loading and loaded snapshots share the same second-level timestamp.

## Changes

- Changed `build_activity_log_entry()` to preserve the original Rich markup string in protocol activity entries instead of flattening it to plain text before observer transport.
- Updated `ServerActivityLogSink` to strip Rich markup only at server-log emission time so server logs stay readable while remote clients still receive colorized content.
- Fixed snapshot-to-view trade-route sync so the client opens the `HAUL ROUTES` picker when a remote search transitions from loading to loaded, even if `query_url` and `searched_at` match the prior loading snapshot exactly.
- Added regression coverage for markup preservation, server-log mirroring, and the same-second remote route-picker transition; full suite passed in `0.321s` for `557` tests.

## Follow-ups

- Live-check one real `control_room serve` plus `control_room connect` session to confirm the restored colors and route-picker modal behave correctly under real Inara latency.
