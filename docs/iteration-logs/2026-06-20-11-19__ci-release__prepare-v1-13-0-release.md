# Iteration Log

- Area: `ci-release`
- Title: `prepare-v1-13-0-release`
- Started: `2026-06-20 11:19`

## Summary

- Prepared the `v1.13.0` release cut from `main` after the browser-facing remote observer expansion, haul/runtime follow-up fixes, and Discord workflow-failure notifier extraction landed since `v1.12.0`.

## Changes

- Bumped `[project].version` in `pyproject.toml` to `1.13.0` so the release-prep commit matches the next semantic tag.
- Updated `docs/status/ci-release.md` to record that `main` is now prepared for `v1.13.0` and to summarize the release scope at the handoff level.
- Refreshed release bookkeeping artifacts and validation as part of the cut.

## Follow-ups

- Push the release-prep commit and `v1.13.0` tag, then publish the GitHub release with high-level notes focused on Control Room remote operations and notifier reliability.
