# Iteration Log

- Area: `control-room`
- Title: `hub-owns-the-markets-page`
- Started: `2026-11-11 21:05`

## Summary

- On a hub, `/markets` with a peer picked was relayed to that peer: it listed the peer's own recent markets file and returned 502 while the peer was offline. Peers already push every market up, but the hub only wrote them into the SQLite store, never into the list the page reads, so the hub and peer views differed.
- The hub now owns the Markets page: `/api/recent-markets` and `/api/market-compare` are no longer node reads. The hub's recent markets list holds its own captures and every peer's pushed markets. The picked node only sets the ship that prices trips (hold, laden range, measured runs' ship); the registry keeps a node's last reported ship, so an offline node still prices the page.

## Changes

- `edap/recent_markets.py`: `record_market` (shared by `record_market_json`) serialises read-modify-write under a lock, since the hub's game capture and its link thread both write the file. The limit is now required and comes from `control_room.recent_markets_limit` (default 20, was a fixed 10).
- `edap/hub/nodes.py`: `store_link_item` takes a `record_market` callback; `NodeRegistry.last_ship`.
- `edap/hub/relay.py`: `node_state` reports `cargo_capacity` and `laden_jump_range_ly`; the two markets paths left `NODE_READS`.
- `edap/control_room/server/app.py`: `markets_ship(params)`; both endpoints are plain hub routes.

## Follow-ups

- A peer's own `/markets` still lists only that machine's captures.
- The last reported ship lives in memory: after a hub restart an offline node falls back to the hub's own ship until it links again. Peers older than this change report no hold or range.
