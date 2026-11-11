# 0015: Hub Command Centre

## Status

Proposed (2026-11-11). Builds on hub mode (`docs/user/hub.md`): peers already forward searches to the hub and push visited markets, and a heartbeat feeds the sidebar Hub chip. Nothing below is built yet.

## Why

Today every machine runs its own Control Room with its own pages, haul history and activity log. With more than one machine you open several sites, and the data is spread across them. Only one machine plays at a time, so one place should show and drive whichever machine is playing.

Goal: the hub is the one control room. Peers are end nodes: they send their data up and run the commands the hub sends down. You open only the hub's pages.

## Decisions (confirmed with the user)

- The hub can play too. It is a node like the others ("local node"), so the same flow works whichever machine runs the game.
- Peers keep their own web pages as a fallback when the hub is down. Normal use does not need them.
- LAN only. A peer runs commands only from the hub it connected to, and the hub accepts only peers that present the hub token.
- The hub can voice the selected node's callouts, behind a switch, on its speakers or in a hub page.

## Design

### Roles and config

```toml
[hub]
role = "peer"        # "hub", "peer", or unset (standalone, as today)
url = ""             # optional on a peer: skip discovery and use this hub
token = "<hub-token>"
name = ""            # node name shown on the hub; defaults to the host name
```

A hub keeps `[eddn]` and the Inara browser as today. A peer without `url` finds the hub by discovery (phase 5). The current `url`-only config keeps working as `role = "peer"`.

### Peer link

The peer opens one websocket to the hub (`/api/peer-link`) and keeps it open, reconnecting with backoff. The peer always dials out, so the hub needs no peer address, peer token or open peer port.

- `hello` (peer to hub): stable `node_id` (generated once, stored next to the config), name, version and capabilities.
- Up: state updates, activity entries, market snapshots, haul runs.
- Down: commands and relayed requests from hub pages.
- The link replaces the heartbeat. `HubStatus` and the Hub chip read the link state instead of pings.

### Pages on the hub drive the selected node

The existing pages already talk to their server over the session websocket (`hydrate`, broker events, `command.*` messages such as `command.submit_input`, `command.dispatch_haul_loop`, `command.cancel_active_routine`). The hub relays that protocol instead of reinventing it:

- A page on the hub opens its session with `?node=<node_id>`. For the local node nothing changes. For a peer, the hub opens a channel over the peer link; the peer attaches a broker observer for that channel and runs incoming `command.*` messages through its normal handler. Pages stay almost unchanged.
- The page-level HTTP reads a page needs (haul stats, recent markets, market compare, route compare, Spansh route, hub status) are relayed the same way as request/response frames, limited to an allowlist.
- Sidebar node picker: online nodes with name, ship and current routine. The user picks the node by hand; no automatic choice yet.

### Data on the hub

- Markets: sent over the link (`POST /api/markets` stays for older peers). Newest snapshot wins, as today.
- Haul runs: the peer still writes its own `haul_runs_file` (source of truth). The hub stores runs from every node in its history, tagged with `node`, deduplicated by the existing run key (`started_at`, `ended_at`, `station_1`). The hub acknowledges what it stored; on reconnect the peer sends runs after the last acknowledged one, so offline runs are not lost.
- History views on the hub can filter by node or show all.

### TTS on the hub

The node keeps speaking its callouts as today. The node also sends each callout's text up the link, and the hub can voice it, behind a switch that is off by default:

- **Hub speakers**: the hub speaks the text with its own voice (platform voice or `[tts.piper]`).
- **Listen in the browser**: the hub synthesizes the text with Piper and sends the WAV to hub pages that opted in, which play it. Piper already writes one WAV per line (`edap/tts.py`), so this is per-callout audio, not a continuous stream, with a delay of about one synthesis. Without Piper on the hub, the page falls back to browser speech (`web/speech.js`).

Only callouts from the selected node are voiced on the hub, so two nodes never talk over each other.

### Discovery

The hub advertises `_edcr._tcp.local` over mDNS with its port and a TXT record (`role=hub`, version, hub name). A peer with no `url` browses for it and connects. The token still has to match. The peer remembers the hub it first connected to and logs loudly if a different one appears, so a stray advertiser on the LAN cannot quietly take over. New dependency: `zeroconf`.

## Phases

Each phase is usable on its own.

1. **Link and registry**: `/api/peer-link`, `hello`, reconnect, node registry on the hub, `GET /api/nodes`, nodes listed on the hub. The heartbeat is replaced by the link state.
2. **See a peer**: relay the session protocol and the allowlisted reads for `?node=`, plus the sidebar node picker. Read-only first: commands from relayed sessions are refused.
3. **Drive a peer**: allow `command.*` over relayed sessions (haul start/stop, controls routines, travel). Same busy and refusal rules as local.
4. **Central history**: haul runs up with acknowledgements, node-tagged history on the hub. Markets move onto the link.
5. **TTS on the hub**: callout text up the link, hub speaker switch, Piper WAV to opted-in hub pages.
6. **Discovery and roles**: `role`, mDNS advertise/browse, remembered hub.

## Open points

- Picking the playing node automatically (needs a "game running" signal) is left for later.
- Whether the node should mute itself while the hub voices its callouts.

## Validation

- Unit tests with an in-memory link (no sockets): hello and registry, reconnect, relay of session messages and reads, refusal while read-only, run acknowledgements and resend, duplicate runs ignored, callouts voiced only for the selected node and only with the switch on.
- Live: a hub and one peer on the LAN; open only the hub's pages, start and stop a haul on the peer, check the peer's runs and markets appear on the hub, then restart the hub mid-haul and check nothing is lost.
