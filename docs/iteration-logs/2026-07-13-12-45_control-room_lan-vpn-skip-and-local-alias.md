# Iteration Log

- Area: `control-room`
- Title: `lan-vpn-skip-and-local-alias`
- Started: `2026-07-13 12:45`

## Summary

- `control_room.py lan` was advertising `198.19.0.1:8765` on a Mac running Cloudflare WARP because `_detect_lan_host` returned the first non-loopback candidate from the UDP-route probe, and WARP owned the default route.
- Reworked `_detect_lan_host` to enumerate from UDP probe + `getaddrinfo` + POSIX `ifconfig`, reject loopback/link-local/CGNAT/RFC 2544 benchmark ranges, and prefer RFC1918 addresses. Verified live on the reporter's machine: candidates included `192.168.0.107` (Wi-Fi), `100.117.11.86` (Tailscale), and `198.19.0.1` (WARP); picker now returns `192.168.0.107`.
- Added `control_room.py local` as an explicit loopback bind mode alongside `serve` / `lan`, mirroring the `lan` alias pattern.

## Changes

- `edap/control_room/app.py`: added `_classify_lan_candidate`, `_iter_ifconfig_ipv4`, ranked candidate selection in `_detect_lan_host`, and the new `local` CLI mode with matching `--host` guardrail.
- `tests/test_control_room.py`: patched new `_iter_ifconfig_ipv4` in existing detection tests, added WARP-skip and RFC1918-over-public cases, and covered the `local` alias plus its `--host` rejection.
- `docs/operators/control-room.md`, `docs/operators/control-room-remote.md`: documented the `local` mode and the new LAN-detection preferences.
- `docs/status/control-room.md`: updated the plan 0008 bullet to mention `local` and the VPN/CGNAT skip.

## Follow-ups

-
