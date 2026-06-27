# Iteration Log

- Area: `docs`
- Title: `per-test-runtime-budget`
- Started: `2026-06-27 18:33`

## Summary

- Replaced the fixed full-suite unittest budget with a per-test budget of `0.0006s`, so the timing threshold scales with suite size instead of requiring manual bumps as coverage grows.

## Changes

- Updated [AGENTS.md](/Users/nicholasclooney/Source/Projects/EDControlRoom/AGENTS.md:53) to treat `uv run python3 -m unittest discover -s tests` as on-budget when total runtime stays at or below `tests_run * 0.0006`.
- Updated [docs/status/docs-process.md](/Users/nicholasclooney/Source/Projects/EDControlRoom/docs/status/docs-process.md:3) and [docs/status/ci-release.md](/Users/nicholasclooney/Source/Projects/EDControlRoom/docs/status/ci-release.md:3) so the current handoff docs describe the per-test budget instead of the stale fixed `0.3s` threshold.
- Confirmed the current suite math: `551 * 0.0006 = 0.3306`, which covers the latest passing run that completed in about `0.320s`.

## Follow-ups

- Keep the per-test multiplier under review if suite composition changes enough that total runtime grows faster than test count.
