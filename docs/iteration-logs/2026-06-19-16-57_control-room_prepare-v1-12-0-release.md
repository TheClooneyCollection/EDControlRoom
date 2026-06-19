# Iteration Log

- Area: `control-room`
- Title: `prepare-v1-12-0-release`
- Started: `2026-06-19 16:57`

## Summary

- Prepared the `v1.12.0` release cut for the Control Room client/server split refactor milestone.
- Captured the release handoff update in `docs/status/ci-release.md` and refreshed generated iteration docs.

## Changes

- Bumped `[project].version` to `1.12.0` for the next stable tag.
- Regenerated `uv.lock` so the lockfile version metadata matches the release prep commit.
- Refreshed `docs/iteration-archive.md` after adding this release-prep iteration log.

## Follow-ups

- Tag `v1.12.0`, push the release-prep commit, and publish the GitHub release notes for the server/client split milestone.
