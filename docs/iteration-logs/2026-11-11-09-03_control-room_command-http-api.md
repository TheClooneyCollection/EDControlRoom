# Iteration Log

- Area: `control-room`
- Title: `command-http-api`
- Started: `2026-11-11 09:03`

## Summary

- Added `POST /api/command` (run any Control Room command text) and `POST /api/stop` (cancel the running routine) so curl, scripts and automation tools can drive routines. Both use the existing token auth.

## Changes

- `/api/command` takes `{"raw_input", "skip_delay"?}` and calls the same `command_handler.submit_input` as websocket `command.submit_input`. 400 on bad body, 409 when refused because a routine is running, 503 without a command handler; responses carry `accepted`, `routine_active`, `active_routine_name`.
- Refusal signal: `RuntimeUIState.busy_refusals` counts busy refusals. `ControlRoomApp._refuse_busy` logs and bumps it; every idle-only check uses it (`workers.check_routine_ready`, remote `_check_routine_ready`, `reload_config`, `reload_keymap`, `haul search`, `stop` while a haul runs). `HeadlessControlRoomHost.submit_input` now returns `bool` (False when the counter moved); `ObserverSessionCommandHandler.submit_input` returns `bool`.
- The text `stop` only freezes haul session stats, so `/api/stop` (`mode` `now` default or `after_run`) calls `cancel_active_routine`, and returns 409 when idle.
- Docs: `docs/user/command-api.md`, linked from `docs/user/README.md` and `README.md`.

## Follow-ups

- The websocket `command.submit_input` reply still always says `accepted: true`; it could use the new return value.
- Headless host treats prompt-owning verbs (`haul`, `dest`, `home`, `market`, ...) as client-local, so the API cannot run them yet.
- CORS still allows only GET/OPTIONS, so cross-origin browser pages cannot POST; curl/Shortcuts are unaffected.
- Not yet tried against a live server.
