# Iteration Log

- Area: `runtime`
- Title: `preserve-migration-backups-on-retry`
- Started: `2026-11-27 23:42`

## Summary

- Address M9 slice A review: preserve the original rollback database and keep smoke checks from creating WAL sidecars.

## Changes

- Keep an existing target-version backup on retry after a partial ladder failure; prune older backups after a successful write or keep. Document execute-only migration steps.
- Read user_version from the validated SQLite file header when no WAL file exists; use read-only SQLite when WAL data must be included. Report check-mode configuration errors consistently.
- Tests cover retry from partially migrated v2 with original v1 backup, absent WAL sidecars, live WAL version, and malformed configuration. Full suite: 1357 tests, one skipped, 1.171s. Timing diagnostic: 1.121s, existing Node flows lead at 77ms each.

## Follow-ups

- Timing remains above 0.9499s budget; prior main baseline also exceeded budget (1344 tests / 1.125s). No unrelated test optimization. Await coordinator integration; no rebase or deployment performed.
