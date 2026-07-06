# Iteration Log

- Area: `ci-release`
- Title: `prepare-v1-20-0-release`
- Started: `2026-07-06 14:01`

## Summary

- Rewound `main` to `bce43a7` with `git rebase --onto` and prepared the next stable release commit.

## Changes

- Bumped project metadata to `1.20.0`.
- Updated the CI/release handoff for the `v1.20.0` release scope and rewind point.
- Regenerated `docs/iteration-archive.md` and refreshed `uv.lock` after the version bump.
- Verified the release prep with `uv run python3 -m unittest discover -s tests`: `678` tests passed in `0.530s`; because this exceeded the `0.4068s` timing gate, ran the required slow-test report and saw the slowest test at `0.017s`.

## Follow-ups

- Push the rewritten `main` history with care, tag `v1.20.0`, and publish the GitHub release from the release-prep commit.
