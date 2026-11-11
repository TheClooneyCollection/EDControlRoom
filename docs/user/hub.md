# Hub Control Room

With more than one machine that plays Elite (a desktop, another PC, a handheld), make one Control Room the **hub**. The hub is the one control room you open: it keeps the market and station data and the haul history of every machine, and its pages show and drive whichever machine is playing. The other machines are **peers**: they send everything they learn up to the hub and run the commands it sends down.

One machine on its own needs none of this: the default role, **standalone**, is the single-machine Control Room.

## Roles

Set the role in each machine's `config.toml` under `[hub] role`.

| | hub | standalone (default) | peer |
|---|---|---|---|
| Market and station database | yes | yes | none |
| EDDN listener | when `[eddn] enabled` | when `[eddn] enabled` | never |
| Inara haul search | runs it | runs it | asks the hub |
| Haul history | every machine's runs | its own | writes its own file, sends every run up |
| Station facts from its journal | into its database | into its database | sent up |
| Web pages | show and drive any machine | drive itself | fallback when the hub is down |
| Runs routines for its own game | yes | yes | yes |

The hub can play too: its own game is just another node in the node picker.

## Set up the hub

```toml
[hub]
role = "hub"
token = "pick-a-long-secret"   # every peer must present this
name = "Desk"                  # shown on the pages; default: the host name

[eddn]
enabled = true                 # optional: live market prices for /routes
```

Start it on the LAN (see [getting-started.md](getting-started.md)):

```bash
uv run python3 control_room.py lan --token <page-token>
```

`--token` protects the hub's own pages and API, like on any server. `[hub] token` is a separate secret only for peer links.

`lan` binds the detected LAN address (it skips VPN and CGNAT ranges such as `100.64.0.0/10` and `198.18.0.0/15`) and that is the address the hub advertises. `serve --host 0.0.0.0` also works and advertises the detected LAN address. `local` and `serve` on `127.0.0.1` are not advertised, because no other machine could reach them. The log says which: `Hub advertised over mDNS as Desk at 192.168.1.20:8765`.

The hub needs Playwright and Chromium for Inara searches ([install.md](install.md)).

## Set up a peer

```toml
[hub]
role = "peer"
token = "pick-a-long-secret"   # the hub's [hub] token
name = "Deck"                  # default: the host name
# url = "http://192.168.1.20:8765"   # optional: skip discovery and use this hub
```

Start the peer as usual (`lan`, `serve` or `local`); its own `--token` still protects its own pages. The peer opens one link to the hub and keeps it open, redialling with backoff (1, 2, 5, 10, then every 30 s) whenever the hub goes away. The peer always dials out, so the hub needs no peer address and no port opened on the peer.

### Discovery and the remembered hub

Without `url`, the peer finds the hub on the LAN over mDNS (service `_edcr._tcp.local`, with a TXT record holding `role=hub`, the hub's id, name and version). The token still has to match. A macOS peer browses with the system `dns-sd` tool (mDNSResponder), so it needs no Local Network permission for Python; Linux and Windows peers browse with `zeroconf`. A browse takes about 3 s, plus up to 3 s for each advert that no longer answers.

- The first hub that accepts the peer is **remembered** in `.control_room_known_hub.json` next to the peer's `config.toml` (its id, name and last address). The log says `Hub Desk (...) is now this peer's hub`.
- From then on the peer dials only that hub, wherever it moves on the LAN. If another hub appears, the peer logs `WARNING: another hub ... is on the LAN; ignoring it` and stays with its own. A hub that answers with a different id is refused with `WARNING: not linking to ...`.
- With two hubs on the LAN and none remembered yet, the peer does not guess: it logs `several hubs on the LAN (...); set [hub] url to pick one`.
- **To switch to another hub**, stop the peer, delete `.control_room_known_hub.json` next to its `config.toml`, and start it again. Or set `url`, which skips discovery and the remembered hub.

Give the hub a fixed LAN address (a DHCP reservation on the router) when you use `url`. Discovery does not need one.

### Node id

Every hub and peer has a stable node id in `.control_room_node_id` next to its `config.toml`, made on the first start. Do not copy it to another machine: a peer with the hub's own id is refused (`delete the copied node id file on the peer`). Delete a copied file and restart to get a new id.

## Settings

All under `[hub]`; defaults in `defaults/hub.toml`.

| Key | Used on | Meaning |
|---|---|---|
| `role` | all | `standalone` (default), `hub` or `peer` |
| `token` | hub, peer | the secret on the peer link; required on both |
| `name` | hub, peer | the name shown on the hub; default the host name |
| `url` | peer | optional hub address; empty means discovery |
| `outbox_file` | peer | markets, station facts and haul runs waiting for the hub (`.control_room_hub_outbox.sqlite3`) |
| `runs_file` | hub | every peer's haul runs, tagged with their node (`.control_room_hub_runs.jsonl`); the hub's own stay in `control_room.haul_runs_file` |
| `voice_file` | hub | which node the hub voices and the hub speaker switch (`.control_room_hub_voice.json`) |
| `timeout_s` | peer | seconds to wait for the hub on routes, status and station facts (10) |
| `search_timeout_s` | peer | seconds to wait for an Inara search on the hub (180) |
| `heartbeat_s` | peer | seconds of quiet before the peer pings the hub; twice that without an answer redials (30) |

## Using the hub's pages

Open only the hub's pages. Every page has a **node picker** in the sidebar (on phones, at the top of the ☰ More menu): each machine with its name, ship and running routine, the hub's own game first. The choice is kept per browser; picking another node reloads the page onto it. A node that drops shows as offline, the page says `Node Deck is offline` and picks it up again when it links.

- **Driving a node**: on the picked node, the haul page, Controls, Travel and the command box run on that machine with the same rules as its own pages (busy routines refuse idle-only commands, answers come back unchanged). `POST /api/command` and `/api/stop` take `?node=<node_id>` the same way ([command-api.md](command-api.md)). When the node drops mid-command the page gets `Node Deck is unreachable` instead of waiting.
- **Markets and routes**: the hub owns the market and station database, so `/routes` and Best deal read it directly, from the picked node's ship and system.
- **Central history**: the haul page's History panel, `/api/haul-stats` and Best deal's measured profit per hour read every machine's runs. The History panel gets node and ship filters once there are two to pick.

## TTS on the hub

Every machine keeps speaking its own callouts and also sends their text up the link. Under the node picker the hub pages show a voice panel:

- **Voice**: Off (default) or one node. One node at a time, for the whole hub, so two machines never talk over each other.
- **Hub speakers**: the hub speaks that node's callouts on its own speakers, queued behind its own callouts. Its own game is never spoken twice.
- **Listen here** (per browser): the page plays the callouts, as Piper audio when the hub has `[tts.piper]`, otherwise with the browser's own voice. While listening, the haul page's own browser speech stays quiet.

Messages in a node's `[tts] disabled_messages` are never sent up, so the hub and listening pages skip them too. A node does not mute itself while the hub voices it; start it with `--no-tts` to keep its own speakers silent (it still sends its callouts up).

## Offline behaviour

- Market snapshots, station facts and finished haul runs go into the peer's outbox first and leave it only when the hub has stored them. While the hub is away the outbox grows; on reconnect it drains in order. Restarting either machine loses nothing.
- The hub stores idempotently: the newest market snapshot and station fact win, and haul runs are kept once per run and node.
- Live state, activity and callouts are not queued: callouts spoken while the link is down are not voiced on the hub later.
- On the peer, routines and hauls keep running. Its own pages still work as a fallback; panels with hub-owned data (routes, Best deal facts, history, Inara search) say `Hub Desk is unreachable` instead of showing stale data.

## Is it connected?

- **Sidebar Hub chip**: on a peer it shows the link (green up, red down), the last contact and how many outbox items are waiting; on the hub the number of linked peers.
- **Log**: the peer logs `Hub link up: Desk (...)` and `Hub link to ... lost`; the hub logs `Peer Deck connected` and `disconnected`.
- **API** (page token): `GET /api/hub-status` (peer: `connected`, `url`, `hub_name`, `last_contact_at`, `last_error`, `outbox_pending`; hub: `peers_connected`), `GET /api/nodes` on the hub (every node with `connected`, `last_contact_at` and `state`).

## Troubleshooting

| Symptom | Check |
|---|---|
| Peer logs `no hub found on the LAN` | The hub runs with role `hub` on `lan` or `serve --host 0.0.0.0` (not `local`), both machines are on the same LAN (mDNS does not cross VPNs or routed subnets), and the hub log shows `Hub advertised over mDNS`. On a macOS peer, run `dns-sd -B _edcr._tcp local` (Ctrl-C to stop): if the hub is not listed there, the Mac does not see it on the LAN at all. On a macOS hub, the advert works without extra permission, but if other machines cannot reach its pages, allow Local Network access for the terminal app in System Settings → Privacy & Security. Or set `[hub] url`. |
| Peer logs `remembered hub ... not found on the LAN` | The remembered hub is off or not advertising. To use another hub, delete `.control_room_known_hub.json` next to the peer's `config.toml`. |
| `WARNING: another hub ... is on the LAN` | Another Control Room runs as a hub. The peer ignores it; nothing to do unless you want to switch. |
| `several hubs on the LAN` | Set `[hub] url` on the peer, or stop the extra hub. |
| `Hub ... refused the link: ...` | A wrong `[hub] token` on the peer, or a copied `.control_room_node_id` (delete it on the peer). |
| Chip red, outbox growing | The hub is down or unreachable; items wait and are sent on reconnect. |
| Config error `hub.token is required` | Set `[hub] token` on the hub and on every peer. |
