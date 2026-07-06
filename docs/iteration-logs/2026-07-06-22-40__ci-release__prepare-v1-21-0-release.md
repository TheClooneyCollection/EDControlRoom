# Iteration Log

- Area: `ci-release`
- Title: `prepare-v1-21-0-release`
- Started: `2026-07-06 22:40`

## Summary

- Prepared `v1.21.0` as the next stable release after `v1.20.0`.

## Changes

- Bumped `[project].version` and `uv.lock` metadata from `1.20.0` to `1.21.0`.
- Updated release status with the new release scope and current test timing.
- Ran the full unittest suite and required slow-test report because the suite exceeded the per-test timing budget.

## Follow-ups

- Watch the post-push `Tests` workflow and Discord notifier path for the `v1.21.0` release commit/tag.
