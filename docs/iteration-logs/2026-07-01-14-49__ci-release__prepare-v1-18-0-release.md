# Iteration Log

- Area: `ci-release`
- Title: `prepare-v1-18-0-release`
- Started: `2026-07-01 14:49`

## Summary

- Prepared the `v1.18.0` release after haul recovery fixes and the config-defaults refactor landed on `main`.

## Changes

- Bumped project metadata from `1.17.0` to `1.18.0`.
- Refreshed `uv.lock` so package metadata matches the release version.
- Updated CI/release handoff status for the new stable release target.
- Passed `uv run python3 -m unittest discover -s tests` with `622` tests in `0.264s`, under the `0.3732s` timing budget.

## Follow-ups

- `v1.18.0` was tagged, pushed, and published as `EDControlRoom v1.18.0 - Config Defaults and Haul Recovery`.
