# Iteration Log

- Area: `ci-release`
- Title: `ci-timing-guard-and-suite-speed`
- Started: `2026-11-11 11:38`

## Summary

- The flaky `Tests` runs were never test failures. All five failures in the last 50 runs were the `test_timing` job: `tools/check_test_timing.py` times `uv run python3 -m unittest discover` end to end against 5s. The suite itself ran ~2s on CI; the rest was a fresh runner compiling `.pyc` files for dependencies and the repo. Passing runs sat at 4.0-4.8s, so runner noise tipped some over (5.1-6.1s).
- Locally a cold bytecode cache adds ~1s (0.94s warm vs 1.97s cold); precompiling brings it back to ~1.15s.
- Local suite time went from `0.64-0.66s` to `~0.60s` for 1076 tests (budget `0.6456s`).

## Changes

- `.github/workflows/tests.yml`: `test_timing` installs with `uv sync --extra dev --compile-bytecode` and runs `compileall` on `edap tests tools control_room.py` before the guard.
- Tests built `ControlRoomApp` or `HeadlessControlRoomHost` with `DefaultVersionSource`, which runs real `git rev-parse`/`git status` (~15ms, once per process). `HeadlessControlRoomHost` now requires `version_source`; `serve.py` passes `DefaultVersionSource()`, tests pass `_FakeVersionSource`.
- `edap/config.py`: bundled YAML tables load with libyaml's `CSafeLoader` when available (~8ms to ~1ms).
- EDDN thread tests: status interval 10ms to 1ms and market watcher poll 5ms to 1ms (the waits were the interval itself).
- Noise removed from test output: the spansh error tests assert the `logger.exception` output with `assertLogs` (the stray `httpx.HTTPStatusError: 400` traceback), in-memory EDDN stores are closed with `addCleanup` (26 `ResourceWarning: unclosed database`), and `rendering.is_recent` uses `datetime.now(UTC)` instead of deprecated `utcnow()`.

## Follow-ups

- GC costs ~30ms per suite run (one gen2 pass lands on whichever test is running; it looks like a random 10-12ms slow test). `gc.freeze()` after discovery saved ~10-25ms in an experiment but needs a custom runner, so it was left out.
- `QueuedSpeaker` threads from tests that never close their `TTSAnnouncer` stay alive (they wake every 0.1s); harmless today.
