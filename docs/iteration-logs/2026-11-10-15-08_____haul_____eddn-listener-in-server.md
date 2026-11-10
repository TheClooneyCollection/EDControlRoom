# Iteration Log

- Area: `haul`
- Title: `eddn-listener-in-server`
- Started: `2026-11-10 15:08`

## Summary

- Plan 0014 step: the Control Room server now runs the EDDN listener itself when `eddn.enabled = true`, so the price table stays current without a separate `tools/eddn_listen.py`.
- Storage check from the standalone listener: 553 markets, 41k prices, 619 stations, 1769 systems use 1.9 MB (~3.5 KB per market) plus a ~4 MB WAL that SQLite checkpoints. A bubble-wide week of markets should stay around 50 to 100 MB.

## Changes

- New `edap/eddn/service.py`: `start_eddn_service(config, open_socket=, time_fn=, log=)` opens the store and starts the listener; `EddnService.status()` returns listener stats plus store counts, `close()` stops, joins and closes the store.
- `serve_observer_mode` configures logging earlier, starts the service when enabled (logs through `edap.eddn`) and closes it on shutdown. `GET /api/eddn-status` (auth like other `/api/*`) returns `{"enabled": false}` or the status.

## Follow-ups

- Run only one writer per database: stop `tools/eddn_listen.py` before starting the server with EDDN enabled.
- Next in plan 0014: route finder, profit/hour ranking, `/routes`.
