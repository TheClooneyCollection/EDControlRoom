# Iteration Log

- Area: `control-room`
- Title: `hub-peer-link-and-outbox`
- Started: `2026-11-11 12:51`

## Summary

- Plan 0015 step 2: peers now reach the hub over one outbound websocket (`/api/peer-link`) instead of HTTP calls. Market snapshots and station facts travel through a persistent outbox; haul search, EDDN routes/status and Best deal station facts are request/response frames.
- The old hub HTTP path is removed with no backward compatibility.

## Changes

- `edap/hub/` package replaces `edap/hub.py`: `protocol.py` (frames, `LinkConnection`, fact encoding), `outbox.py` (SQLite, key dedupe for 30 days), `peer.py` (`PeerLink`: hello, drain, ack/nack, requests with ids and timeouts, quiet ping, backoff 1/2/5/10/30 s reset after a welcome, `websocket_connector`), `nodes.py` (`NodeRegistry`, `HubLinkSession` pure frame handler, `store_link_item`).
- Node id: generated once, stored at `<config dir>/.control_room_node_id`. A hello carrying the hub's own id is refused (copied file).
- Config: `[hub] name`, `[hub] outbox_file`; `[hub] token` now required on a hub and on a peer with `url`. `heartbeat_s` is the link ping interval.
- Server: `GET /api/nodes` (hub only), `/api/hub-status` per role, peer answers tagged `hub: <hub name>`. Removed `POST /api/markets`, `POST /api/haul-search`, `GET /api/hub-ping`, HubClient, HubMarketPusher, heartbeat thread. `watch_recent_markets` moved to `edap/recent_markets.py`.
- `web/hub-status.js` shows link state, last contact and outbox pending (peer) or peer count (hub).
- Live smoke on one machine (hub and peer on loopback ports): link up, queued items stored, routes/status/market-compare answered by the hub, hub killed (peer shows down, outbox grows, 502), hub restarted (relink drains the outbox, newest price wins).

## Follow-ups

- `docs/user/hub.md` still describes the old HTTP mode; rewrite in step 8.
- A TUI-only peer (no server) keeps no station facts and has no link.
- Link latency is no longer reported.
