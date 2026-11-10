# Control Room Status Archive

Prepend displaced older status blocks from `docs/status/control-room.md` here.

Legacy pre-split global status history remains in `../../status-archive.md`.

## Archived 2026-11-10

- `set_pid` and `set_hwnd` are available operator commands; bare forms auto-target `EliteDangerous64.exe`, explicit pid/hwnd values are accepted, and `foreground` clears the override.

## Archived 2026-11-09

- Control Room supports `home` / `home set`, `dest home`, repo-local `haul load [path]`, replay/edit prefill for multi-step haul prompts, and failure messages with `Failed:` plus `Try:` guidance; direct `dock` waits for `SupercruiseExit` only from supercruise state and starts immediately from normal space, while `dest` retries unset `NavRoute.json` verification with Fibonacci-style galaxy-map settles after the configured first attempt and Spansh 400s become actionable target-system messages.

## Archived 2026-11-09

- Snapshot protocol support is removed: `serve` no longer advertises or serves `/snapshot`, websocket `state.snapshot`, or `command.request_snapshot`; snapshot dataclasses, `snapshot_from_app`, snapshot schema defs, and backend/server retained snapshot paths are gone.

## Archived 2026-11-08

- Replay browser actions are app-local, not backend-owned: backend replay open/close/filter/move/replay/default-haul methods were removed after the connect single-app collapse.
