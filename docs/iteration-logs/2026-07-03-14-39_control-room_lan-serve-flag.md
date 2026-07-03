# Iteration Log

- Area: `control-room`
- Title: `lan-serve-flag`
- Started: `2026-07-03 14:39`

## Summary

- Added `control_room.py serve --lan` so LAN serving can bind to the detected non-loopback IPv4 address without manually passing `--host`.

## Changes

- Added LAN host detection in the Control Room CLI using UDP route probing with hostname-address fallback.
- Made `serve --lan` and `serve --host` mutually exclusive, preserving the default local bind of `127.0.0.1`.
- Updated remote observer operator docs to recommend `--lan` for same-network clients while retaining explicit `--host 0.0.0.0` guidance.
- Added focused CLI tests for LAN detection, serve wiring, and conflict handling.

## Follow-ups

- Live LAN validation should confirm the chosen bind address is the operator-visible address on the current macOS/CrossOver host.
