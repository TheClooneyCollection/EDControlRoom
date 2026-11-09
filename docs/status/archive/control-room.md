# Control Room Status Archive

Prepend displaced older status blocks from `docs/status/control-room.md` here.

Legacy pre-split global status history remains in `../../status-archive.md`.

## Archived 2026-11-09

- Snapshot protocol support is removed: `serve` no longer advertises or serves `/snapshot`, websocket `state.snapshot`, or `command.request_snapshot`; snapshot dataclasses, `snapshot_from_app`, snapshot schema defs, and backend/server retained snapshot paths are gone.

## Archived 2026-11-08

- Replay browser actions are app-local, not backend-owned: backend replay open/close/filter/move/replay/default-haul methods were removed after the connect single-app collapse.
