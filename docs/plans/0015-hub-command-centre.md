# 0015: Hub Command Centre

## Status

Designed (2026-11-11). Built: step 1 (roles and data ownership, 2026-11-11), step 2 (peer link and outbox, 2026-11-11), step 3 (ship on every run, 2026-11-11), step 4 (central history, 2026-11-11), step 5 (see a node, 2026-11-11), step 6 (drive a node, 2026-11-11), step 7 (TTS on the hub, 2026-11-11), step 8 (discovery and docs, 2026-11-11). All build steps are done; the live run with two machines (Validation) is pending and is done by the user before the branch lands. One feature: it replaces today's hub mode (`docs/user/hub.md`) as a whole and is released only when every build step below is done. The end state is designed here at once; no step keeps the old hub mode working alongside it.

## Why

Today every machine runs its own Control Room with its own pages, haul history, activity log and station data. With more than one machine you open several sites and the data is spread across them. Only one machine plays at a time, so one place should show and drive whichever machine is playing.

Goal: the hub is the one control room. Peers are end nodes: they send everything they learn up, and they run the commands the hub sends down. You open only the hub's pages.

## Decisions (confirmed with the user)

- Three roles: **hub**, **peer** and **standalone** (no hub, today's single-machine use). Hub and standalone own data; a peer owns none.
- The hub can play too. Its own game is the hub's local node, handled the same way as a peer.
- Peers keep their own web pages as a fallback when the hub is down. Normal use does not need them.
- LAN only. A peer runs commands only from the hub it connected to; the hub accepts only peers that present the hub token.
- The hub can voice the selected node's callouts, behind a switch, on its speakers or in a hub page.
- Measured profit per hour is per ship and over a time window (default 7 days).
- The node picker is manual. Picking the playing node automatically is out of scope.

## Design

### Roles and config

```toml
[hub]
role = "standalone"   # "hub", "peer" or "standalone" (default)
token = "<hub-token>" # hub: required from peers; peer: sent to the hub
url = ""              # peer only, optional: skip discovery and use this hub
name = ""             # node name shown on the hub; defaults to the host name
```

| | hub | standalone | peer |
|---|---|---|---|
| Market and station database (SQLite) | yes, always open | yes, always open | none |
| EDDN listener | when `[eddn]` is on | when `[eddn]` is on | never |
| Ardent lookups | yes | yes | never |
| Inara browser search | yes | yes | asks the hub |
| Haul history | central, every node | its own | writes its own file, sends every run up |
| Station facts from its journal | into its database | into its database | sent up |
| Web pages | drive any node | drive itself | fallback, reads from the hub |
| Runs routines for its own game | yes | yes | yes |

The database opens from the role, not from `[eddn]`: `[eddn]` only starts the listener. Old `[hub] url`-only configs and `POST /api/markets`, `GET /api/hub-ping` go away.

### Peer link

The peer opens one websocket to the hub (`/api/peer-link`) and keeps it open, reconnecting with backoff. The peer always dials out, so the hub needs no peer address, peer token or open peer port. All peer to hub traffic uses this link; there is no other HTTP between them.

- `hello` (peer to hub): stable `node_id` (generated once, stored next to the config), name, version.
- Up: live state and activity, callout text, market snapshots, station facts, haul runs.
- Down: commands and relayed page requests.
- Peer to hub requests over the link: Inara search, EDDN routes, station facts for Best deal.
- Link state is the hub connection status: the peer's Hub chip shows it, the hub lists nodes with last contact.

### Outbox on the peer

Everything the peer sends up that must not be lost (market snapshots, station facts, haul runs) goes into a small persistent outbox first and leaves it when the hub acknowledges it. While the hub is away the outbox grows; on reconnect it drains in order. The hub stores idempotently: newest market snapshot and newest station fact win, haul runs are deduplicated by their key (`started_at`, `ended_at`, `station_1`) plus `node_id`. Live state, activity and callouts are not queued.

### Station facts

One store of system and station facts (`system` and `station` tables of the existing SQLite schema: coordinates, distance from star, type, pad, surface), on the hub or standalone only. Sources, newest wins:

- EDDN messages (listener).
- Journals: `Docked` (distance from star, station type, pads), `FSDJump` / `Location` / `CarrierJump` (system coordinates), `Market.json` station type. The local node writes them directly; a peer sends them up.
- Ardent (`edap/ardent.py`), asked only when a needed fact is still missing, and written into the same tables.

The recent-markets file holds market snapshots only; its `places` key goes away. Best deal and `/routes` read facts from this one store.

### Pages on the hub drive the selected node

The existing pages already talk to their server over the session websocket (`hydrate`, broker events, `command.*` messages). The hub relays that protocol instead of reinventing it:

- A hub page opens its session with `?node=<node_id>`. For the local node nothing changes. For a peer, the hub opens a channel over the peer link; the peer attaches a broker observer for that channel and runs incoming `command.*` messages through its normal handler with the same busy and refusal rules as local.
- Node-specific HTTP reads a page needs (live haul stats, recent markets, route compare, Spansh route) are relayed as request/response frames, limited to an allowlist. Data the hub owns (markets database, history, routes, Best deal) is answered by the hub directly.
- Sidebar node picker: online nodes with name, ship and current routine; the choice is kept per browser.
- On a peer's own fallback pages, hub-owned data (routes, Best deal facts, history) is fetched from the hub over the link; when the hub is away those panels say so instead of showing stale local data.

### Haul history and measured profit per hour

- Every run records its ship: ship ID, type, name, cargo capacity, max jump range (`Loadout.MaxJumpRange`) and laden jump range.
- Hub history views show every node, with filters for node and ship.
- Storage: the hub appends peers' runs to `[hub] runs_file` (the `haul_runs_file` JSONL format plus `node: {id, name}`) and reads its own `haul_runs_file` under its own node id, so every node's own file stays its source of truth. A peer's history views and measured profit per hour ask the hub.
- Best deal's measured profit per hour uses completed runs on the station pair, either direction, for the current ship, over a window picked next to it (48h, 7 days default, 30 days, all). It shows the run count, average loop time and the ship's laden jump range, so a ship that now jumps further is visible. Older runs without ship data count within the window, marked "ship unknown".

### TTS on the hub

The node keeps speaking its callouts. It also sends each callout's text up the link, and the hub can voice the selected node's callouts, behind a switch that is off by default:

- **Hub speakers**: the hub speaks the text with its own voice (platform voice or `[tts.piper]`).
- **Listen in the browser**: the hub synthesizes the text with Piper and sends the WAV to hub pages that opted in. Piper already writes one WAV per line (`edap/tts.py`), so this is per-callout audio with a delay of about one synthesis. Without Piper on the hub, the page uses browser speech (`web/speech.js`).

### Discovery

The hub advertises `_edcr._tcp.local` over mDNS with its port and a TXT record (`role=hub`, version, hub name). A peer with no `url` browses for it and connects. The token still has to match. The peer remembers the hub it first connected to and logs loudly if a different one appears, so a stray advertiser on the LAN cannot quietly take over. New dependency: `zeroconf`.

As built: the TXT record also carries the hub's node id, which the hub sends in `welcome`. The peer remembers the first hub that welcomes it in `.control_room_known_hub.json` next to its config, dials only that hub afterwards, logs and ignores any other hub, and refuses a welcome with another id; deleting the file switches hubs. With two hubs and none remembered it does not guess. A peer with `url` skips discovery and the remembered hub. The hub advertises its `lan` bind address (or the detected LAN address for `0.0.0.0`) and never a loopback bind.

## Build steps

Built on a feature branch `feat/hub-command-centre`, one agent per step in order, each step committed on that branch with tests. The branch lands on `main` (rebased, fast-forward) only after step 8.

1. **Roles and data ownership**: `[hub] role`, database opened by role, station facts store with journal and Ardent writers, `places` removed from recent markets, Best deal and `/routes` read the one store. Standalone fully works.
2. **Peer link and outbox**: `/api/peer-link`, `hello`, reconnect, node registry and `GET /api/nodes`, persistent outbox with acknowledgements. Markets and station facts travel over it. Search, routes and Best deal facts are asked over it. Old hub HTTP endpoints and heartbeat removed; Hub chip reads the link.
3. **Ship on every run**: ship fields recorded per run; measured profit per hour with ship filter and window on Best deal.
4. **Central history**: haul runs up through the outbox, node-tagged history on the hub with node and ship filters.
5. **See a node**: relay of the session protocol and allowlisted reads for `?node=`, sidebar node picker. Commands over relayed sessions refused in this step.
6. **Drive a node**: `command.*` over relayed sessions (haul, controls, travel).
7. **TTS on the hub**: callout text up, hub speaker switch, Piper WAV to opted-in pages.
8. **Discovery and docs**: mDNS advertise and browse, remembered hub, `docs/user/hub.md` rewritten for the new mode, live run with two machines.

## Open points

- Whether the node should mute itself while the hub voices its callouts.

## Validation

- Unit tests with an in-memory link (no sockets): hello and registry, reconnect, outbox drain and acknowledgement, idempotent stores, relay of session messages and reads, refused commands in step 5, callouts voiced only for the selected node and only with the switch on, measured profit per hour by ship and window.
- Live (step 8): a hub and one peer on the LAN; open only the hub's pages, start and stop a haul on the peer, check its runs, markets and station facts reach the hub, restart the hub mid-haul and check nothing is lost.
