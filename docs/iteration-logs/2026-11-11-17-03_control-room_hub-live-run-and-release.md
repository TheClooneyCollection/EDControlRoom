# Iteration Log

- Area: `control-room`
- Title: `hub-live-run-and-release`
- Started: `2026-11-11 17:03`

## Summary

- Live run of plan 0015 with a Mac hub and a Windows peer. The peer found the hub over mDNS (`zeroconf`), hub pages picked and drove it, and the hub voice played the peer's callouts on the hub and in a browser with the peer muted.
- Fixes found by the run: the node picker stayed hidden (nav.js read the web config before the page set it), a peer opened hub pages as observers so Search routes and the stop buttons were disabled, and a hub page's Stop now waited for the routine it stopped (separate log). `say` now publishes its line like a callout, so Controls Say and Test voice exercise the hub voice.
- The default market buy hold is a flat 3.5 s (the log curve held about 9 s for 1100 t); haul tops up a short buy.
- CI: Windows failed one outbox test that closed its SQLite file after the temp directory was removed. Fixed. The Windows unittest job takes about 10 minutes on `main` too.
- Landed `feat/hub-command-centre` on `main` and released it as v1.34.0.

## Follow-ups

- Not exercised live: a hub restart mid-haul (outbox tests cover it).
- A listening browser plays to the device's current audio output; with a headset or other output active it may seem silent.
