# Iteration Log

- Area: `control-room`
- Title: `lan-serve-also-listens-on-localhost`
- Started: `2026-11-13 09:51`

## Summary

- `lan`, `hub` and `peer` bound only the detected LAN address, so `tailscale serve` had to proxy to the LAN IP (`127.0.0.1:8765` refused) and broke whenever that IP changed. A LAN-bound server now also listens on `127.0.0.1` by default.

## Changes

- New `[control_room] lan_also_localhost` (default `true`). `bind_hosts` in `edcr/hub/discovery.py` returns the bind host plus `127.0.0.1` unless the host is loopback or `0.0.0.0`; `serve.py` binds one uvicorn socket per host and runs one `uvicorn.Server` over both.
- mDNS still advertises the LAN address only. Documented in `docs/user/hub.md`.

## Follow-ups

- After restarting the hub, point the Tailscale serve entry at `http://127.0.0.1:8765`.
