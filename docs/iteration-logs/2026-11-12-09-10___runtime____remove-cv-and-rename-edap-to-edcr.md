# Iteration Log

- Area: `runtime`
- Title: `remove-cv-and-rename-edap-to-edcr`
- Started: `2026-11-12 09:10`

## Summary

- Removed the CV screen-capture pipeline: EDControlRoom reads the journal and `Status.json`, never the screen.
- Removed leftover EDAP files from the repo root.
- Renamed the runtime package `edap/` to `edcr/`, including the Wine input helper (`C:\edcr\edcr_input_helper.exe`).

## Changes

- Deleted `edap/capture.py`, `edap/platform/screen/`, `defaults/screen.toml`, the `[screen]` config section, `tools/diagnostics.py --capture-screen`, `tools/scratch/scratch_cv.py`, `tools/scratch/scratch_rebake.py`, the CV templates, `testdata/`, and the `dev` extra (numpy, opencv, pytesseract, Pillow). CI now runs plain `uv sync`. A leftover `[screen]` table in `config.toml` is ignored (covered by `test_ignores_legacy_screen_table`).
- Deleted `archive/legacy-windows/`, `src/` logos and the stale `requirements.txt` (Windows installs use `uv sync`). Moved the multi-leg haul example to `docs/examples/`. Plans 0001-0003 and research 0004 link to commit `56843e7` for the legacy code.
- `git mv edap edcr` plus a word-boundary replace across code, tests, tools, CI, `.agents` and current docs. Logger names are now `edcr.*`. Historical iteration logs, devlogs, plans and research keep `edap` paths.
- Rebuilt and installed the renamed helper into the Test bottle; the old `C:\edap\` copy is left in place, unused.

## Follow-ups

- Optionally delete `<bottle>/drive_c/edap/` from the Test bottle.
- Runtime state files (`.control_room_*`, `.eddn_markets.sqlite3*`) still sit in the repo root; moving them into a state directory is deferred.
