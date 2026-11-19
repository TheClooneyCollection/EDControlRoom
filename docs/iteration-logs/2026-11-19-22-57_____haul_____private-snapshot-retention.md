# Iteration Log

- Area: `haul`
- Title: `private-snapshot-retention`
- Started: `2026-11-19 22:57`

## Summary

- Implemented the EDCR portion of plan 0021: optional local snapshot retention and private Tailscale operator instructions.

## Changes

- `write --keep N` accepts positive integers and prunes only after writing the manifest; omission retains all artifacts. Shared pruning keeps the existing publish upload-before-prune behavior.
- CLI tests cover retention counts, manifest artifact integrity, unrelated files, invalid values and failed writes; publish tests remain unchanged.
- Added private snapshot timer/Serve/hub configuration guidance and consolidated the haul snapshot status within its 20-line cap.
- Focused suite: 13 tests in 0.052s, OK (1 opt-in integration skipped). Full suite: 1295 tests in 1.042s, OK (1 skipped).
- Timing budget remains unmet (0.777s): prescribed timing report identified existing haul web/two-way hotspots; stashed baseline also exceeded its budget (1292 tests in 1.158s). Existing SQLite ResourceWarnings appeared in the full suite.

## Follow-ups

- Interface review and integration; no merge, push, deployment or live verification performed.
- Deployment owns the write timer, persistent Serve process and local hub URL. Address the pre-existing full-suite timing excess separately.
- Retention uses the existing UTC filename order; the writer assumes chronological timestamps and one writer per directory.
