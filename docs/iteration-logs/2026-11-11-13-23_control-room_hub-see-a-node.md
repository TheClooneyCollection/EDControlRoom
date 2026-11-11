# Iteration Log

- Area: `control-room`
- Title: `hub-see-a-node`
- Started: `2026-11-11 13:23`

## Summary

- Plan 0015 step 5: a hub page can look at a peer. `?node=<node_id>` on the session websocket and on node reads relays them over the peer link; commands are refused (view-only). A sidebar node picker on hub pages picks the node per browser.

## Changes

- `edap/hub/relay.py`: `HubRelay` (hub side: linked peers, page channels, reads in flight) and `PeerRelay` (peer side: answers `channel_open`/`channel_close` with a broker listener plus connection ready and hydrate, answers `read` frames on a background thread so a read may ask the hub back). Up frames: `channel`, `read_response`, `node_state`. Channel opens that arrive before the welcome wait for it; a reconnect ends pages on the old connection, and a stale close is ignored by generation.
- Allowlist `NODE_READS`: recent-markets, market-compare, route-compare (+ config), spansh-route, eddn-routes (the peer asks the hub back, so routes start from the node's ship). Checked on both sides; anything else 403. Hub-owned reads (haul-stats, markets DB, eddn-status) are answered by the hub; on haul-stats `node` stays the history filter.
- Refusals: `command.*` on a relayed session gets `response.error` `node_view_only`; `POST /api/command` and `/api/stop` with `node=` give 403. Unreachable node reads give 502 "Node X is unreachable: <reason>".
- Offline: the relayed session stays open, the page gets one activity line ("Node X is offline (...); showing it again when it links.") and the hub retries every 2 s, sending a fresh connection ready and hydrate on relink.
- `node_state` (ship id/type/name, active routine) is sent on link up and whenever it changes (broker listener); `/api/nodes` shows it per node (null when offline), the local node computes it.
- Broker `add_listener`; `PeerLink` takes a required `relay` and `send_frame`; `HubSide` takes `relay`; node read routes share async cores taking params.
- Web: `web/nav.js` picker (hub only, polls `/api/nodes` every 10 s, "Name · Ship · routine", chosen node shown offline), stored under localStorage `edcr.node` in try/catch, page reloads on change. Desktop: below the nav; phones: top of the More menu. Session and read URLs carry `node` via `window.EDCRNode`.
- Verified: `tests/test_hub_relay.py` (in-memory link). Live smoke with two local `serve` processes on loopback: relayed hydrate, reads, refused command, offline line, relink hydrate. Headless browser at 1280 and 390 px: picker, reload onto the peer, offline label, no horizontal scroll, no page errors.

## Follow-ups

- Step 6: run `command.*` on relayed sessions (drop the refusal).
- `/haul` journal ledger for a peer view still shows the hub machine's ledger (hub-owned haul-stats).
- `node_state` is sent per broker event (deduped); a busy node could send it often.
