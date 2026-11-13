# Iteration Log

- Area: `ci-release`
- Title: `cut-state-save-and-store-setup-in-tests`
- Started: `2026-11-13 20:14`

## Summary

- The suite (`1183` tests, budget `0.710s`) ran at `0.87s`. Profiling `test_control_room` showed state saves as the largest cost: every haul event saves, and each save paid `json.dumps(indent=2)` (pure-Python encoder) plus temp file, `fsync` and rename, about `0.19ms` each.
- Now `0.68s`. `test_control_room` went from `0.214s` to `0.143s` (`0.64ms` per test).

## Changes

- `save_control_room_state` writes compact JSON (C encoder) through an injected `write_text`; `write_text_atomically` keeps the temp file, `fsync` and rename.
- `ControlRoomApp` and `HeadlessControlRoomHost` take a required `write_state_file`. Production passes `write_text_atomically`; tests pass `tests.fakes.write_text_plain`.
- `tests/__init__.py` sets `gc.set_threshold(50000, 20, 100)`: at the defaults GC cost about `60ms` per suite (gen2 alone `~31ms`); the raised threshold saves about `40ms`.
- `tests/test_eddn.memory_store` copies a prebuilt schema with `sqlite3` backup instead of running the schema script per store (`0.29ms` to `0.11ms`).

## Follow-ups

- Hub relay tests stay about `3.4ms` each: setUp `~0.9ms`, each WebSocket session `~0.8ms`, each `TestClient` enter and exit `~0.4ms`.
