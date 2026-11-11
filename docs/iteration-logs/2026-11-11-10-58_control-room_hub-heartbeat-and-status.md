# Iteration Log

- Area: `control-room`
- Title: `hub-heartbeat-and-status`
- Started: `2026-11-11 10:58`

## Summary

- A peer now checks its hub instead of only logging the configured URL. A heartbeat pings the hub, one thread-safe `HubStatus` records what the peer last heard, `GET /api/hub-status` reports it, and every sidebar page shows a Hub chip.

## Changes

- `edap/hub.py`: `HubStatus` holds reachable (`None` until the first check), checked/last-ok times, last error, latency, last push (stations, written/kept or error) and resend pending. `ping_hub` asks `GET /api/hub-ping` and logs `Hub <host> reachable (<ms> ms)` / `Hub <host> unreachable: <reason>` only when reachability changes, so the first result after start is always logged. `run_hub_heartbeat` loops with injected `perf_counter` and `wait` (the stop event's `wait` in production). Exceptions are logged and never end the loop. `HubMarketPusher` now takes `status`: a 200 push marks the hub reachable, an unreachable push marks it down, and a refused push (hub answered, non-200) records the push error but leaves reachability to the heartbeat.
- `[hub].heartbeat_s` (default 30, positive and finite) in `defaults/hub.toml` and `HubConfig`. Pings use `timeout_s`.
- Server: `GET /api/hub-ping` (`{"status": "ok"}`) and `GET /api/hub-status` (`{"configured": false}` without a hub) on every server, both with normal auth. `serve.py` starts thread `hub-heartbeat` next to `hub-markets`, stopped by the same event.
- Web: `web/hub-status.js` (new shared asset) polls `/api/hub-status` every 10 s and fills `#hub-chip`, which sits above the sidebar foot on `/haul`, `/multi-haul`, `/controls`, `/markets` and `/routes`. It stays hidden without a hub. Green means reachable, red unreachable, grey unknown, and the `title` tooltip holds last ok, last push and pending resend. On phones it sits in the scrolling nav row; the sidebar foot stays hidden there.
- Tests in `tests/test_hub.py`: heartbeat sequence with a fake transport, fake perf counter and fake wait; status before the first check; pusher status reporting; `/api/hub-status` against a real in-process hub (good and wrong token); every sidebar page loads the chip.

## Follow-ups

- Not tried in a browser or live yet: check the chip layout on desktop and phone widths, and the log lines on a real peer.
- A non-200 ping (for example a wrong token, or an older hub without `/api/hub-ping`, which answers 404) shows as unreachable with the HTTP reason.
- The full-suite runtime was already over the 0.0006 s/test budget on `main` before this change (about 0.66 s for 1071 tests).
