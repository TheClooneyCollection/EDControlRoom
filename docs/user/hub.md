# Hub Control Room

Run one Control Room at home as the **hub**. It searches routes (Inara and EDDN) and keeps the market database. Other Control Rooms, the **peers** (another PC, a laptop or a handheld), point at it: they ask the hub for routes and send it the markets they visit.

## What goes where

| | Hub | Peer |
|---|---|---|
| Inara haul search (`/haul`) | runs the browser search | sends the search to the hub |
| EDDN routes (`/routes`) | searches its database | asks the hub, for the peer's own ship |
| Markets you open in game | written to its own database | sent to the hub's database only |
| `haul_search.toml` defaults | used for its own searches | still fill the peer's form and blank `/routes` fields |
| Flying, hauling, TTS | its own ship | its own ship, nothing changes |

A peer sends its current system, cargo capacity and filled-in search settings with every request, so the hub answers for the peer's ship, not the hub's.

## Set up the hub

1. Turn on the market database in the hub's `config.toml`:

   ```toml
   [eddn]
   enabled = true
   ```

2. Start it so the peers can reach it on the LAN (see [getting-started.md](getting-started.md)):

   ```bash
   uv run python3 control_room.py lan --token <hub-token>
   ```

   Without `--token` the hub uses the default `edcr` token. `lan` binds only the detected LAN address and skips VPN and CGNAT ranges (`100.64.0.0/10`); for peers on such a network, use `serve --host 0.0.0.0`.

The hub needs Playwright and Chromium for Inara searches ([install.md](install.md)). It needs no hub settings itself.

## Point a peer at the hub

In the peer's `config.toml`:

```toml
[hub]
url = "http://192.168.1.20:8765"   # the address the hub's lan server printed
token = "<hub-token>"   # "edcr" when the hub runs without --token
```

Give the hub a fixed LAN address (a DHCP reservation on the router) so this URL keeps working.

Restart the peer. Its log says `Hub: searches and market pushes go to ...`. The peer's own `--token` still protects the peer; `[hub].token` is only for talking to the hub.

Peers usually leave `[eddn]` off: the hub listens to EDDN for everyone. `[eddn]` stays independent, so a peer that turns it on keeps a local EDDN listener, but its own visited markets still go only to the hub.

Optional settings: `timeout_s` (default 10 s, routes, market pushes and heartbeats), `search_timeout_s` (default 180 s, Inara searches) and `heartbeat_s` (default 30 s between reachability checks).

## Is the peer connected?

The startup line `Hub: searches and market pushes go to ...` only repeats the config. To see whether the hub actually answers:

- **Log**: the peer pings the hub at start and every `heartbeat_s`, and logs only when that changes: `Hub <host> reachable (12 ms)` or `Hub <host> unreachable: <reason>`. A wrong `[hub].token` shows as `unreachable: HTTP 401: authentication required`.
- **Sidebar chip**: every page with a sidebar shows `Hub <host>` on a peer: green when reachable, red when not, grey before the first check. Hover it (long-press on a phone) for the last good contact, the last market push and whether a resend of recent markets is pending. Pages on a server without `[hub]` show no chip.
- **API**: `GET /api/hub-status` (see below).

A successful market push also counts as contact, so the chip can turn green before the next heartbeat.

## Pages on a peer

- `/routes` shows `via hub <host>` after the route count, and the EDDN chip shows the hub's market count.
- `/haul` search results show `via hub <host>`.
- When the hub cannot be reached, the page shows `Hub <host> is unreachable: ...` instead of results. Nothing else on the peer stops: routines, hauls and pasted routes keep working.

## Offline behaviour

- Each time the peer records a market (you open the commodities market in game), it sends that market to the hub.
- If the hub is down, the peer logs the failure and remembers it. The next successful push sends all recent markets (the last 10), so nothing visited while offline is lost as long as it is still in that list.
- The hub keeps the newest snapshot per station, so a resend never replaces fresher data.
- At start the peer sends all recent markets once.
- A failed push is retried at the next market you open, not on a timer.
- Pushes run in the background with timeouts; a slow or missing hub never blocks the ship.

## API

- `POST /api/haul-search`: JSON body like the websocket `command.search_haul_routes` payload (`system_name`, `cargo_capacity`, `max_route_distance_ly`, ...). Returns `{"result": ...}`; 400 for a bad search, 502 when Inara or the hub fails. It does not save `haul_search.toml`.
- `GET /api/eddn-routes`: `system`, `capacity` and `laden_jump_range_ly` (and the other filters) override the hub's own ship and settings.
- `POST /api/markets`: `{"markets": [<recent markets entry>, ...]}`, the shape of `.control_room_recent_markets.json`. Returns `{"results": [{"station", "system", "timestamp", "written"}]}`; 400 for a bad body, 503 when the hub has no EDDN database.

- `GET /api/hub-ping`: `{"status": "ok"}`; what a peer's heartbeat asks for.
- `GET /api/hub-status`: on any server. `{"configured": false}` without `[hub]`; otherwise `host`, `url`, `heartbeat_s`, `reachable` (`null` before the first check), `checked_at`, `last_ok_at`, `last_error`, `latency_ms`, `last_push` (`at`, `stations`, `written`, `kept`, `error`) and `resend_pending`. Times are ISO UTC. Takes the peer's own token.

All take the server's token like every other `/api/*` call: the hub's token for the hub endpoints.
