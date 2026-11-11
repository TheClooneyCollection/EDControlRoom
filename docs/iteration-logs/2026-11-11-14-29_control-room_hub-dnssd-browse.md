# Iteration Log

- Area: `control-room`
- Title: `hub-dnssd-browse`
- Started: `2026-11-11 14:29`

## Summary

- A macOS peer now browses for the hub with the system `dns-sd` tool instead of `zeroconf`, because Python's own mDNS socket received no multicast on a Mac (likely Local Network permission) while `dns-sd`, which asks mDNSResponder, sees the LAN. Linux and Windows keep `zeroconf`.

## Changes

- `edap/hub/discovery.py`: `dnssd_browse(seconds, run)` runs `dns-sd -B _edcr._tcp local` for the browse window (Add/Rmv rows, instances on several interfaces deduplicated), then `dns-sd -L <instance>` (host, port, TXT with `\ `, `\\` and `\xHH` escapes) and `dns-sd -G v4 <host>` (a LAN address preferred over the loopback row a same-Mac hub also reports). Returns the same `HubAdvert` list, so `DiscoveredHub` and `KnownHub` are unchanged. `run_until(args, seconds, done)` is the production runner: `dns-sd` never exits, so it reads output with `select` until `done(output)` or the deadline, then kills it; a missing command returns "". `lan_browse(platform, seconds)` picks `dns-sd` on darwin, `zeroconf` elsewhere; `serve.py` calls it with `sys.platform`.
- Why prefer over fall back: a zeroconf-first browse would cost its 3 s window on every redial before `dns-sd` runs, and on a Mac mDNSResponder already owns port 5353 and caches the records.
- Tests: `DnssdBrowseTests` (2) feed scrubbed recorded `dns-sd` output through a fake runner: removed, silent (never answers) and non-hub instances, escaped TXT, loopback skipped, and the `done` predicates (browse listens its whole window, lookups stop on the answer). Suite: 1145 tests in 0.607 s (budget 0.687).
- Docs: `docs/user/hub.md` discovery note and the `no hub found` troubleshooting row (check with `dns-sd -B _edcr._tcp local` on a macOS peer).

## Live check (one Mac)

- Hub `serve --host 0.0.0.0` with role `hub` advertised its LAN address; `lan_browse("darwin", 3.0)` returned it with the right id, name, version and port in about 6 s (3 s browse, plus 3 s for a stale advert on the LAN whose lookup never answers).
- A peer `serve` without `url` found the hub through `dns-sd`, dialled its LAN address, remembered it and linked (`Hub link up`); the hub logged the peer connected. The earlier note that a server on the LAN address never answered did not reproduce here.

## Follow-ups

- Live two-machine run, with a macOS peer and a Linux or Windows peer.
- A stale advert costs one lookup deadline per browse; a shorter lookup deadline than the browse window would trim that if it matters.
