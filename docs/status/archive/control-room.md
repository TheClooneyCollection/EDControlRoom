# Control Room Status Archive

Prepend displaced older status blocks from `docs/status/control-room.md` here.

Legacy pre-split global status history remains in `../../status-archive.md`.

## Archived 2026-11-11 (hub roles, plan 0015 step 1)

- Remote observer clients can start without a local Elite journal path and reconnect with exponential backoff; websocket recovery relies on server hydrate messages, while client shutdown state stays local, priority `Ctrl-C`/`Ctrl-D` bindings avoid command-input collisions, and remote-active `Ctrl-D` opens the detach prompt then exits the client on the next press without cancelling the server routine.

## Archived 2026-11-11 (hub heartbeat)

- Hub mode (`docs/user/hub.md`, since 2026-11-11, not yet tried live): with `[hub] url`/`token` set (`defaults/hub.toml`, empty = local), the server forwards `/api/eddn-routes` (ship and `haul_search.toml` inputs resolved locally by `resolve_route_params`), `/api/eddn-status` and the Inara haul search (websocket and `POST /api/haul-search`) to the hub, tagging answers `hub: <host>` (pages show `via hub`), 502 / `hub_unreachable` when it is down. Its visited markets go only to the hub (`HubMarketPusher`, thread `hub-markets`, `POST /api/markets`, newest wins; all recent markets at start and after a failed push, retried on the next market, not on a timer). Any server takes `POST /api/haul-search` and, with `[eddn]` on, `POST /api/markets` (503 without). Transport is `edap.hub.httpx_transport`, injected for tests. Commodity display names for `/routes` Copy still come from the hub's own recent markets.

## Archived 2026-11-11 (hub mode)

- Market panel lock semantics are aligned across embedded and `connect`: `market lock` pins the displayed panel to the current market identity, same-market updates still render, and different-market data is held back until unlock.

## Archived 2026-11-11

- `ControlRoomApp` no longer stores/applies backend snapshots, the backend contract no longer exposes `current_snapshot()`, and `ControlRoomEventSink` uses explicit `publish_data_refresh()` to fan out data-source hydrate messages.

## Archived 2026-11-10

- Activity log redraws preserve first-observed display order across local prompt logs and remote server logs, so connect-mode hydrate refreshes do not reorder entries by cross-machine wall-clock timestamps.
- `set_pid` and `set_hwnd` are available operator commands; bare forms auto-target `EliteDangerous64.exe`, explicit pid/hwnd values are accepted, and `foreground` clears the override.

## Archived 2026-11-09

- Control Room supports `home` / `home set`, `dest home`, repo-local `haul load [path]`, replay/edit prefill for multi-step haul prompts, and failure messages with `Failed:` plus `Try:` guidance; direct `dock` waits for `SupercruiseExit` only from supercruise state and starts immediately from normal space, while `dest` retries unset `NavRoute.json` verification with Fibonacci-style galaxy-map settles after the configured first attempt and Spansh 400s become actionable target-system messages.

## Archived 2026-11-09

- Snapshot protocol support is removed: `serve` no longer advertises or serves `/snapshot`, websocket `state.snapshot`, or `command.request_snapshot`; snapshot dataclasses, `snapshot_from_app`, snapshot schema defs, and backend/server retained snapshot paths are gone.

## Archived 2026-11-08

- Replay browser actions are app-local, not backend-owned: backend replay open/close/filter/move/replay/default-haul methods were removed after the connect single-app collapse.
