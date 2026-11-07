# Iteration Log

- Area: `tools`
- Title: `file-path-tool-entrypoints`
- Started: `2026-11-07 23:24`

## Summary

- The documented `uv run python3 tools/<tool>.py` form failed with `ModuleNotFoundError: No module named 'edap'` for 8 tools, because running a file path puts `tools/` on `sys.path` instead of the repo root. Only `-m tools.<tool>` worked.

## Changes

- `bindings_files`, `check_bindings`, `diagnostics`, `run_routine`, `set_binding`, `speak`, `view_bindings` and `watch_journal` now add the repo root to `sys.path` before importing `edap`. This is the same `REPO_ROOT` bootstrap that `ship_controls`, `haul_stats`, `iteration_logs` and `report_test_timing` already used. Both invocation forms work, so the docs stay as written.
- `tests/test_tools_entrypoints.py` fails if any `tools/*.py` imports `edap` without the bootstrap first. It scans source text and starts no subprocess, so it stays within the test-time budget.

## Follow-ups

- `tools/scratch/scratch_cv.py` and `scratch_rebake.py` fail on a missing `cv2`. That is a dependency gap, not a path problem, so it was left alone.
- The full suite runs over the 0.0006s/test budget even at HEAD before this change (0.895s for 931 tests, with Elite running on this machine).
