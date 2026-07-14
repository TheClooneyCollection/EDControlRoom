# Iteration Log

- Area: `ci-release`
- Title: `prepare-v1-22-0-release`
- Started: `2026-07-14 15:23`

## Summary

- Prepared `v1.22.0` as the next minor release after `v1.21.0`.

## Changes

- Bumped `[project].version` in `pyproject.toml` and will refresh `uv.lock` to match.
- Captured the release scope in `docs/status/ci-release.md`: Spansh neutron travel, route comparison, active-route UI, and Inara haul filters.
- Regenerated the iteration archive and validated the full unittest suite before the release cut.

## Follow-ups

- Tag and publish `v1.22.0` from the release-prep commit with concise operator-facing notes.
