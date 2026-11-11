# Iteration Log

- Area: `control-room`
- Title: `hub-lan-binding-docs`
- Started: `2026-11-11 11:01`

## Summary

- The hub guide now says what `lan` binds and when to use `serve --host 0.0.0.0` instead. Runtime status now notes that routines cannot be driven from a Windows SSH session. Peer examples in the user docs are generic.

## Changes

- `docs/user/hub.md`: `lan` binds only the detected LAN address and `_detect_lan_host` skips `100.64.0.0/10` (VPN and CGNAT ranges), so peers on such a network need `serve --host 0.0.0.0`. Also covers the default `edcr` token and a DHCP reservation for the hub.
- `docs/status/runtime.md`: new caveat that sshd runs outside the logged-in desktop session, so routines started over SSH cannot reach Elite. Start Control Room on the desktop and drive it through the web pages or `POST /api/command`. Merged two Windows next-step bullets to stay within 20 lines.
- `docs/user/hub.md`, `docs/user/README.md`, `docs/user/trade-routes.md` and the hub iteration log: peer examples reworded to generic machines.

## Follow-ups

- Try a hub and a peer live: a peer pushes a market and `/routes` works through the hub.
