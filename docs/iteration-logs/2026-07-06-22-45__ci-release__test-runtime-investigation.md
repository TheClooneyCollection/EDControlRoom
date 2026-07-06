# Iteration Log

- Area: `ci-release`
- Title: `test-runtime-investigation`
- Started: `2026-07-06 22:45`

## Summary

- Investigated why the `701`-test unittest suite exceeds the repo timing budget.
- Confirmed the full suite still passes and is timing-sensitive: earlier runs reported `0.698-0.770s` with `1.230s` wall through `tools/check_test_timing.py`, while a later warm run reported `0.401s`.

## Changes

- Captured a timing report with `tools/report_test_timing.py --top 20 --sort slowest`; the slowest individual test was only `0.024s`.
- Grouped timings by module/class and found the cost is distributed: `test_control_room` dominates by volume, especially command/bindings/dispatch tests that construct full Textual `ControlRoomApp` harnesses per test.
- Profiled the suite with `cProfile`; import/discovery, repeated app setup, and cache-sensitive filesystem/module work are the main contributors, with no single test sleep or obvious pathological outlier.
- Updated `docs/status/ci-release.md` with the current timing diagnosis.

## Follow-ups

- To lower runtime materially, split pure command/dispatch behavior away from full Textual app fixtures or add lightweight test harnesses that bypass repeated `ControlRoomApp` construction.
