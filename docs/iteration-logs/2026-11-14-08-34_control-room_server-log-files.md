# Iteration Log

- Area: `control-room`
- Title: `server-log-files`
- Started: `2026-11-14 08:34`

## Summary

- The headless server (`serve` / `lan` / `hub` / `peer`) now writes its log to files as well as stderr. On 2026-11-13 the cause of empty `/haul` searches (`Inara access check detected in headless mode`) was only in a tmux pane's scrollback.
- Split like a web server's error and access logs: `[control_room] log_file` (default `.control_room_server.log`: EDCR loggers plus `uvicorn.error`) and `access_log_file` (default `.control_room_access.log`: `uvicorn.access`, noisy with polling). Both rotate at 5 MB, 3 kept; `""` turns one off.

## Changes

- `edcr/control_room/server/log_files.py`: rotating handlers on the root logger, `uvicorn` and `uvicorn.access`. uvicorn's loggers do not propagate to the root, and every `uvicorn.Config(...)` reapplies its dictConfig and drops their handlers, so `serve.py` now builds all Configs first, attaches the handlers, then binds the sockets (so `Uvicorn running on` lands in the file too).
- Config keys in `edcr/config.py`, `defaults/control_room.toml`, `config.example.toml`; both files git-ignored; `docs/user/troubleshooting.md` gains Read the Server Log, `docs/user/hub.md` points at it.
- Checked with a scratch uvicorn app: startup, shutdown and request lines land in the right file, stderr unchanged. Not yet tried on the live hub.

## Follow-ups

- Restart the hub to pick it up.
