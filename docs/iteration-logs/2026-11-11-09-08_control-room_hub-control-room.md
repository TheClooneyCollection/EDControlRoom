# Iteration Log

- Area: `control-room`
- Title: `hub-control-room`
- Started: `2026-11-11 09:08`

## Summary

- One home Control Room (the hub) now runs route searches and holds the market DB for peers (Steam Deck, travel Mac). A peer with `[hub] url`/`token` forwards searches with its own ship inputs and pushes the markets it visits to the hub. Not yet tried live between two machines.

## Changes

- Config: `defaults/hub.toml` → `HubConfig` (`url`, `token`, `timeout_s` 10, `search_timeout_s` 180); `url` must be http(s), trailing `/` stripped; empty means local behaviour.
- `edap/hub.py`: `HubRequest`/`HubResponse`/`HubTransport` (plain function; `httpx_transport` in production, httpx was already a dependency), `HubClient`, `HubMarketPusher`, `watch_recent_markets` (also used by `EddnService.import_game_markets_every` now).
- Hub side: `POST /api/haul-search` (REST twin of `command.search_haul_routes`, does not save `haul_search.toml`; 400 `invalid_search`, 502 otherwise) and `POST /api/markets` (`{"markets": [recent-markets entries]}` → `import_markets` → per-station `written`; 400 bad body, 503 without `[eddn]`).
- Peer side: `/api/eddn-routes` resolves blank params from its own `haul_search.toml` and ship (`resolve_route_params`, same key mapping as `parse_route_query`) and forwards them; `/api/eddn-status` and both haul search paths forward too; answers get `hub: <host>`; unreachable → 502 / `hub_unreachable`. `/routes` and `/haul` show `via hub <host>`.
- The websocket search sync/async handlers now share `_haul_search_from_payload` and `_run_haul_search` with the REST endpoint.
- Market push: peers skip the local `eddn-game-markets` import and run thread `hub-markets`; first push and the first after a failure send all recent markets, otherwise only new `(market_id, timestamp)` entries.
- Docs: `docs/user/hub.md`, linked from `docs/user/README.md`, `README.md`, `trade-routes.md`; `config.example.toml` `[hub]`.

## Follow-ups

- Live-check a Deck peer against the home hub: `/routes`, `/haul` search, market push, hub down mid-haul.
- A failed push is retried only on the next market change, not on a timer.
- Blank route params a peer cannot resolve fall back to the hub's own `haul_search.toml`.
- `/routes` display names (Copy / Open in haul) come from the hub's recent markets, not the peer's.
