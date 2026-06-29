# Iteration Log

- Area: `ci-release`
- Title: `prepare-v1-16-0-release`
- Started: `2026-06-29 08:56`

## Summary

- Prepared the `v1.16.0` release from `main` by bumping package metadata, validating the test/docs pipeline, and capturing the release state in maintained status docs.

## Changes

- Bumped `[project].version` to `1.16.0` and refreshed the lock metadata with `uv sync`.
- Regenerated `docs/iteration-archive.md` after adding this release-prep iteration log and refreshed `docs/status/ci-release.md` for the new release target.
- Ran `uv run python3 -m unittest discover -s tests` plus iteration-log validation; the release-prep suite passed `599` tests in `0.291s`, which stays under the `0.3594s` timing budget.

## Follow-ups

- Push the release-prep commit, tag `v1.16.0`, and publish the GitHub release with operator-facing notes for the local observer haul search move, timing randomization, and UI/runtime fixes.
