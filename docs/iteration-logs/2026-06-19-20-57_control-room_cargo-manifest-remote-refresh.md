# Iteration Log

- Area: `control-room`
- Title: `cargo-manifest-remote-refresh`
- Started: `2026-06-19 20:57`

## Summary

- Fixed the cargo-state mismatch where Control Room could show total cargo tonnage from `Status.json` while cargo details stayed empty, causing remote `sell` and resumed haul decisions to treat the hold as empty.

## Changes

- Added `edap/cargo_manifest.py` as a shared cargo-manifest reader that retries briefly when `Status.json` reports cargo but `Cargo.json` is temporarily empty.
- Switched bootstrap, render/status refresh, trade routines, market routines, and two-way haul resume detection over to the shared manifest reader.
- Updated `ControlRoomApp._sync_status_snapshot()` to refresh cargo details alongside `Status.json` so server/client snapshots recover commodity breakdown without waiting for a fresh trade event.
- Added regression coverage for the retry helper and for status refresh repopulating cargo inventory.

## Follow-ups

- Live-test remote server startup and resumed haul with preloaded cargo to confirm the new retry path matches Elite/CrossOver file-write timing in practice.
