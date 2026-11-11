# Control Room Status Archive

Prepend displaced older status blocks from `docs/status/control-room.md` here.

Legacy pre-split global status history remains in `../../status-archive.md`.

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
