# Iteration Log

- Area: `control-room`
- Title: `hub-discovery-and-docs`
- Started: `2026-11-11 13:54`

## Summary

- Plan 0015 step 8, the last build step: the hub advertises itself over mDNS and a peer without `[hub] url` finds it and remembers it; disabled TTS messages are no longer published; `docs/user/hub.md` rewritten for the hub command centre. Only the live two-machine run remains (the user does it).

## Changes

- `edap/hub/discovery.py`: `HubAdvert`, `advert_properties` (TXT `role=hub`, `id` = the hub's node id, `name`, `version`), `advert_from_record`, `KnownHub` (JSON file `.control_room_known_hub.json` next to the config: first welcome remembered, same id at a new address updates the hint, another id refused with "delete <file> to switch", an unreadable file refuses every hub), `DiscoveredHub` (the link's `connect`: browse, dial the remembered hub or the only one, warn once per stranger, `NoHubFound` for none, a missing remembered hub, or two hubs with none remembered), `zeroconf_browse` (3 s browse, IPv4, resolves each record), `zeroconf_advertise` (registers on the interface owning the address, returns a stop function), `advertise_address` (bind host; detected LAN address for `0.0.0.0`; "" for loopback).
- `PeerLink`: `hub_url` is now a function (discovery changes it) and a required `accept_hub(hub_id, name, url)` runs on `welcome`; a refusal logs `WARNING: not linking to ...`, sets `last_error` and closes. `websocket_connector` became `websocket_dialer(token, timeout_s)(url)`. A `url` peer accepts any hub (the user named it) and keeps no remembered file.
- Config: a peer always links (`enabled` = role peer); `[hub] token` required on hub and every peer. `serve_observer_mode` takes a required `advertise_host`, computed in `main()` from the bind host and `_detect_lan_host` (so `lan`'s VPN/CGNAT skipping decides the advert). Hub logs `Hub advertised over mDNS as <name> at <addr>:<port>`, or why not.
- TTS: `TTSAnnouncer.render_announcement` returns None for `disabled_messages`, so `_announce_tts` never publishes them (pages, hub link, hub voice). The node's own speaker already skipped them.
- Docs: `docs/user/hub.md` rewritten (roles, hub/peer setup, discovery and remembered hub, node id, settings table, node picker and driving, central history, TTS on the hub, offline/outbox, connection checks, troubleshooting). `config.example.toml`, `defaults/hub.toml`, README, `docs/user/README.md`, `getting-started.md`, `command-api.md` (`?node=`, 502) updated. Plan 0015 Status and an "as built" note under Discovery.
- Dependency: `zeroconf` 0.154.0 (`uv add`, lockfile updated).
- Tests: `tests/test_hub_discovery.py` (7, fakes, no network), config and CLI tests updated, a TTS publish assertion. Suite: 1143 tests in 0.675-0.766 s (budget 0.686; the spread is machine load from a parallel test run, no new test in the slowest 10).
- Live smoke on one Mac: the hub advert is seen by `dns-sd -B/-L _edcr._tcp` with the right TXT. Python processes started from the agent shell received no mDNS multicast at all (a raw socket on 5353 got 0 packets) and a server bound to the LAN address accepted TCP but never answered, while loopback worked; most likely macOS Local Network privacy for this terminal. So the hub ran on `serve --host 0.0.0.0` (advertising the detected LAN address) and a scripted `PeerLink` with `DiscoveredHub` and `KnownHub` dialled it on loopback: link up, hub remembered; with another id remembered, the welcome was refused with the delete-the-file hint.

## Follow-ups

- Live two-machine run (plan Validation), including real browse from a peer on Linux or Windows.
- On a macOS peer, browsing needs Local Network permission for the app that starts it; if that proves awkward, a `dns-sd` based browser behind the same `browse` function is a small addition.
- A refused hub (welcome with another id) is redialled with backoff and warned about each time; with discovery the TXT id already filters it out before dialling.
- Open point (plan): whether a node mutes itself while the hub voices it.
