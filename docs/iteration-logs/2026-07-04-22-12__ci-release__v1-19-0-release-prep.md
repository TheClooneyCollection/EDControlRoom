# Iteration Log

- Area: `ci-release`
- Title: `v1-19-0-release-prep`
- Started: `2026-07-04 22:12`

## Summary

- Prepared `v1.19.0` after the post-`v1.18.0` haul web controls/state work and haul route/interdiction recovery fixes.

## Changes

- Bumped `pyproject.toml` and `uv.lock` from `1.18.0` to `1.19.0`.
- Updated `docs/status/ci-release.md` with the `v1.19.0` release summary and current unittest timing gate.
- Ran `uv run python3 -m unittest discover -s tests`: `675` tests passed in `0.377s`, below the `0.405s` timing budget.

## Follow-ups

- Publish the `v1.19.0` tag and GitHub release once the release-prep commit is pushed.
