# Iteration Log

- Area: `control-room`
- Title: `remove-reload-command`
- Started: `2026-11-08 13:00`

## Summary

- Removed the `reload` hot-reload command. Its module list had gone stale and `importlib.reload` never refreshed names bound with `from X import y`, so it gave false confidence. Code changes need a Control Room restart; binding changes use `reload_keymap`.
- The user confirmed uinput input works in Steam Deck Game Mode (gamescope), not only Desktop Mode.

## Changes

- Dropped the `reload` verb, `ControlRoomFacade.cmd_reload`, `_RELOADABLE_MODULES`, the `edap/control_room/tts.py` re-export shim and the `reload_failed` message. `reload` now reports as an unknown command.
- Steam Deck bindings (outside the repo): an in-game save at 12:09 had unbound `YawAxisRaw`, moved `RollAxisRaw` to the right stick and cleared Pitch inversion. Restored those three axes from `Custom.4.2.binds.bak` (right stick X yaw, left stick X roll, pitch inverted), keeping CRLF line endings; pre-restore copy in `Custom.4.2.binds.pre-axis-restore`.

## Follow-ups

- Saving controls in game rewrites the whole binds file from memory, so write bindings with Elite closed or restart it without saving.
