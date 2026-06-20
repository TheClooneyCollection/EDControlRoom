# Iteration Log

- Area: `docs-process`
- Title: `move-auxiliary-clis-into-tools`
- Started: `2026-06-20 11:30`

## Summary

- Moved every supported root-level Python CLI except `control_room.py` into `tools/` so the repo root now presents one obvious primary entrypoint while auxiliary operator and diagnostics scripts live in one utility namespace.

## Changes

- Moved `bindings_files.py`, `check_bindings.py`, `diagnostics.py`, `run_routine.py`, `set_binding.py`, `ship_controls.py`, `speak.py`, `view_bindings.py`, and `watch_journal.py` into `tools/`.
- Added `tools/__init__.py` so the CLI unit tests can import the relocated modules directly.
- Updated maintained README and operator/diagnostics docs to use `tools/...` command paths and recorded the new layout in `docs/status/docs-process.md`.
- Updated CLI unit tests and moved-script self-references to target the `tools.*` modules and executable paths.

## Follow-ups

- Keep future auxiliary CLIs under `tools/` unless there is a strong reason they belong in the runtime package or scratch space, so `control_room.py` remains the only root Python entrypoint.
