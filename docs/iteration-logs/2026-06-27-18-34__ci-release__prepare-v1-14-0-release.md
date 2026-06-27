# Iteration Log

- Area: `ci-release`
- Title: `prepare-v1-14-0-release`
- Started: `2026-06-27 18:34`

## Summary

- Prepared the `v1.14.0` release by bumping project metadata, refreshing the generated lock/archive artifacts, and revalidating the suite on the current per-test runtime budget.

## Changes

- Updated [pyproject.toml](/Users/nicholasclooney/Source/Projects/EDControlRoom/pyproject.toml:3) from `1.13.0` to `1.14.0` for the new release target.
- Refreshed [docs/status/ci-release.md](/Users/nicholasclooney/Source/Projects/EDControlRoom/docs/status/ci-release.md:3) so the handoff reflects the `v1.14.0` scope and the current `551`-test baseline under the computed `0.3306s` budget.
- Regenerated [docs/iteration-archive.md](/Users/nicholasclooney/Source/Projects/EDControlRoom/docs/iteration-archive.md:1) after adding the release-prep and runtime-budget iteration logs, then re-ran the full unittest suite.

## Follow-ups

- Push the release-prep commit and `v1.14.0` tag, then publish the GitHub release with high-level notes focused on the Inara haul-search and remote observer/control-room additions.
