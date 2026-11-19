# Iteration Log

- Area: `ci-release`
- Title: `fix-test-timezone-cost`
- Started: `2026-11-19 23:11`

## Summary

- Remove OS timezone lookup overhead from Control Room/server/hub behavior tests using module-scoped UTC fixtures. Production code and assertions are unchanged.

## Changes

- `tests/fixtures/timezone.py` installs the UTC adapter only during each test module and restores it through `addModuleCleanup`; importing test helpers does not patch runtime code. The OS adapter and DST coverage in `test_haul_history` remains real.
- `SystemLocalTimezone.utcoffset` repeatedly consults the OS; profiling attributed about 74 ms across these files to timezone conversion. Wall-clock runs, including a `git stash` comparison, confirm server/hub improvements; Control Room totals remain noisy.
- Per-file unittest wall times (seconds), three baseline runs with changes stashed followed by three final runs:

| Module | Tests | Before | After |
| --- | ---: | --- | --- |
| test_control_room | 252 | 0.249 / 0.221 / 0.264 | 0.242 / 0.230 / 0.219 |
| test_control_room_server | 70 | 0.125 / 0.132 / 0.159 | 0.100 / 0.098 / 0.096 |
| test_hub_relay | 26 | 0.128 / 0.110 / 0.113 | 0.089 / 0.086 / 0.086 |
| test_hub | 35 | 0.104 / 0.108 / 0.109 | 0.068 / 0.067 / 0.067 |
| test_bindings_files_cli (unchanged, initial baseline) | 9 | 0.022 / 0.022 / 0.024 | 0.022 / 0.021 / 0.022 |

- Commands use `UV_PROJECT_ENVIRONMENT=../../.venv UV_CACHE_DIR=/private/tmp/uv-cache uv run --no-sync python3 -m unittest ...` from the worktree: existing dependencies were reused because the sandbox could not download a new environment.
- Full suite: `Ran 1295 tests in 1.193s`, OK (1 skipped), with localhost socket permission. Required slow-test report: 1295 tests, 1.178s, OK. An initial sandboxed attempt failed only the localhost HTTP integration test.

## Follow-ups

- The full suite remains above its 0.777s budget; separate assigned slices cover haul sleeps and web/snapshot overhead. No production optimization or shared mutable fixture reuse was introduced.
- Real hand-flown journal replay still costs about 13 ms; it continues to exercise event handling and file persistence. bindings CLI had no compelling safe test-only optimization and stays unchanged.
