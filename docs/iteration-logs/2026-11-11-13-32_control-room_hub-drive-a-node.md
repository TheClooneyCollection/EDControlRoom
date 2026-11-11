# Iteration Log

- Area: `control-room`
- Title: `hub-drive-a-node`
- Started: `2026-11-11 13:32`

## Summary

- Plan 0015 step 6: a hub page drives the node it looks at. `command.*` on a relayed session and `POST /api/command` / `/api/stop` with `?node=` run on the peer through its own handlers, with the same busy and refusal rules as a local page; answers come back unchanged.
- Step 5 leftovers fixed: the `/haul` journal ledger in a peer view is the peer's, and the suite is back under its timing budget.

## Changes

- `edap/hub/relay.py`: new hub to peer frames `channel_command` (channel, message) and `act` (id, path, body; answered by `read_response`). `HubRelay.command`, `HubRelay.act`, `command_timeout_s` (search, all-in-one and Spansh plot commands use the slow timeout). `PeerRelay` takes required `answer_command` and `answer_action`; a channel's commands run one at a time in order on the background runner, as a local session awaits each one. Non-command messages get `invalid_command`; commands for a channel not open on the peer are dropped and logged. `NODE_ACTIONS` allowlists `/api/command` and `/api/stop`; `/api/journal-ledger` joins `NODE_READS`.
- Only the dialled link delivers commands: `PeerLink.on_frame` passes relay frames to the relay, a peer has no link endpoint (4404), and the hub ignores `channel_command`/`act` frames sent up by a peer.
- Server: the relayed session forwards commands instead of refusing them. The hub tracks each unanswered command id; on link close it answers `response.error` `node_unreachable` ("Node X is unreachable: the link closed") before the offline line, on timeout "no answer in N s", and while the node is offline at once. HTTP command/stop share cores (`run_command`, `stop_routine`) with the peer's `answer_node_action`; 502 when the node is unreachable. `command.request_active_operator` is refused on a node (hub pages are not peer sessions).
- `/api/haul-stats` takes `view_node` (the node the page looks at, separate from the `node` history filter); for a peer the hub asks it for `/api/journal-ledger` and names it in `journal_node`. `web/haul-ui.js` sends it.
- Timing: step 5's relay tests rebuilt an on-disk SQLite store, recent-markets files and temp dirs per test (about 5 ms each). Read-only fixtures in `RelayTests` and `LinkedServerTests` now come from `setUpClass`. Full suite: 1132 tests in 0.652-0.667 s (budget 0.679).
- Live smoke: hub and peer as two `serve` processes on loopback with scratch configs and an empty journal folder. From a hub session on the peer: `instant` on, `say`, `instant` off ran on the peer, activity and `response.success` came back; `POST /api/command` and `/api/stop` (409 "No routine is running." unchanged) relayed; peer ledger shown; peer killed: HTTP 502 and session `node_unreachable` errors per command.

## Follow-ups

- A command already running on the peer when the link drops still finishes there; the page only learns the link closed.
- HTTP `act` uses the normal link timeout (`[hub] timeout_s`); `/api/command` answers at once, so no slow variant yet.
