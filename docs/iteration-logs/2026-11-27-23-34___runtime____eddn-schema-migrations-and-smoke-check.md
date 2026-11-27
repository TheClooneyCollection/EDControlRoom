# Iteration Log

- Area: `runtime`
- Title: `eddn-schema-migrations-and-smoke-check`
- Started: `2026-11-27 23:34`

## Summary

- Implement M9 slice A: store migrations, snapshot version compatibility and listener smoke check.

## Changes

- Require explicit backup callbacks; open backs up with VACUUM INTO and retains one pre-version copy. Each ladder step and its version commit together before additive schema setup.
- Upgrade older downloaded snapshots; keep exact import validation and reject newer manifests with an actionable hub-update error.
- Add read-only --check reporting, missing-file handling, migration failure/backup tests and snapshot import flow coverage. Update direct test constructors for the required callback.

## Follow-ups

- VPS updater/role implementation and authorized deployment belong to the separate ansible slice. No real schema bump or migration step is introduced.
- Final full suite: 1353 tests pass (one skipped) in 1.092s; timing diagnostic 1.071s versus 0.9471s budget; existing Node web flows lead at 82ms/75ms. Baseline main `ad21253`: 1344 tests pass (one skipped) in 1.125s, also over budget. No unrelated hotspots changed.
