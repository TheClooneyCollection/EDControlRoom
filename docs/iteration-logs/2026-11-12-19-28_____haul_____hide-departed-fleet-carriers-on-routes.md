# Iteration Log

- Area: `haul`
- Title: `hide-departed-fleet-carriers-on-routes`
- Started: `2026-11-12 19:28`

## Summary

- `/routes` listed GONDAMON (Q8N-BVT) in Lachangu from a 13:47 market upload. At 19:23 the forge journal's carrier list for Lachangu did not include it, so it had left. `/routes` now hides carriers known to have moved on.

## Findings

- The game holds `FSSSignalDiscovered` while in supercruise and writes the system's whole batch at once, with one timestamp, at login or the first `SupercruiseExit` of a visit. Later drops in the same system in the same session write none (Crucis Sector FW-W b1-7: 27 to 29 carriers at each login, 0 at every later drop). Systems only passed through in supercruise write nothing.

## Changes

- New `CarrierSighting(callsign, system_address, timestamp, complete)` update. Our own journal's `FSSSignalDiscovered` gives `complete=True` (plus `CarrierName`); EDDN `fsssignaldiscovered/1` gives `complete=False`, since an upload may be partial.
- Store tables `carrier_seen` (latest sighting per callsign; EDDN repeats in the same system are written at most every 10 minutes, complete ones always) and `carrier_scan` (latest complete batch per system).
- `load_route_markets` drops a carrier when, after its market was read, its station row moved to another system (`CarrierJump`), its signal was seen elsewhere, or a complete batch for its system did not include it.
- Peers send `carrier_name` and `carrier_sighting` up the hub link as station facts. The outbox key now falls back to the callsign, so one batch's items do not collapse.

## Follow-ups

- Assumption to watch: a returning visit's batch is again complete. If a later batch ever lists only new carriers, it would hide carriers that are still there.
