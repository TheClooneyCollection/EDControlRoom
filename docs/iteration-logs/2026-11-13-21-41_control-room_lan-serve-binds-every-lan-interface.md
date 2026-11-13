# Iteration Log

- Area: `control-room`
- Title: `lan-serve-binds-every-lan-interface`
- Started: `2026-11-13 21:41`

## Summary

- A hub Mac on Wi-Fi and Ethernet on two subnets bound and advertised only the default-route address, so a peer on the other subnet could neither find nor reach it. `lan`, `hub` and `peer` now listen on and advertise every LAN interface by default.

## Changes

- New `[control_room] lan_all_interfaces` (default `true`). `_detect_lan_hosts` in `edcr/control_room/app.py` lists every accepted interface address (same `_classify_lan_candidate` filter, so Tailscale/CGNAT/WARP stay out), from the route probe and interface enumeration only, not host name lookups, since a stale host name entry would fail the bind. `main` passes it as `lan_hosts` to `serve_observer_mode`; `lan_hosts` in `edcr/hub/discovery.py` keeps the detected host first. Still no `0.0.0.0`.
- Interface enumeration moved to `edcr/platform/lan.py`: `ifconfig` on POSIX (with netmasks), on Windows `gethostbyname_ex(gethostname())` with an assumed /24, since the stdlib has no netmask call there.
- `zeroconf_advertise` takes `addresses`: one `Zeroconf(interfaces=[...])` and one `ServiceInfo` listing them all. The hub logs `Listening on a, b, 127.0.0.1 (port N)` and `Hub advertised over mDNS as X at a, b (port N)`.
- `HubAdvert.address` became `addresses`. `DiscoveredHub` takes `local_interfaces` and dials the address on the peer's own subnet first (`preferred_addresses`), then each other address in record order, raising the last failure. The zeroconf browse keeps every parsed address; `dnssd_browse` keeps every `dns-sd -G v4` row and stops once a row arrives without the MoreComing flag (`0x1`).
- Interfaces are read once at start: a network change needs a restart (documented in `docs/user/hub.md`).

## Live checks

- On this Mac (two interfaces, both on one subnet at the time, plus Tailscale): `_detect_lan_hosts` returned both LAN addresses and skipped Tailscale; a real `zeroconf_advertise` with both registered without error, and `dnssd_browse` with the real `run_until` resolved the test hub with both addresses.
- `dns-sd -G v4 <host>.local.` on a Mac answers from mDNSResponder with the host's own A records for every interface (and loopback), so even the old single-address hub was reported with several addresses to a macOS peer; the old code took the first row, which could be the unreachable one. The subnet preference fixes that too. Rows arrive in one batch, flags `40000003` then `40000002` on the last.
- Not verified live: a peer on a second subnet linking to a hub on two subnets.
- Suite timing ran over budget (0.75 to 0.99 s for 1191 tests, budget 0.71 s) under a machine load average of ~13; the new tests take ~0 ms each.

## Follow-ups

- Try a real two-subnet hub with a peer on the non-default subnet.
