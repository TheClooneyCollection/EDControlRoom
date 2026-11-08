# Iteration Log

- Area: `control-room`
- Title: `reload-keymap-command`
- Started: `2026-11-08 12:27`

## Summary

- Control Room read the bindings file once at startup, so a binding changed while it ran (here: Boost on the Steam Deck) needed a Control Room restart. `reload` only re-imports code modules and never rereads bindings.

## Changes

- New `reload_keymap` command (TUI and web command box): rereads the effective bindings file into `_ctx.binding_lookup`, rebuilds `ShipControls`, and reprints the bindings check. Refused while a routine runs, because a routine keeps the controls it started with. A missing or unparsable file is reported and the old keymap stays. Elite itself still needs a restart to read new bindings.

## Follow-ups

- The user wants `reload` removed. It is stale: `_RELOADABLE_MODULES` misses newer modules (`routines_travel`, `routines_spansh`, `routine_runtime_builder`, `routine_stop`, `view_models`, `view_actions`, `failure_messages`, ...), never reloads `edap/routines/*`, and `importlib.reload` does not refresh names other modules imported with `from X import y`.
