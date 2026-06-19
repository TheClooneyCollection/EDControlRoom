# Iteration Log

- Area: `control-room`
- Title: `fix-remote-routine-state-teardown`
- Started: `2026-06-19 13:46`

## Summary

- Fixed stale remote active-routine state after routine completion and guarded remote cancel against a missing server-side worker.

## Changes

- Published a fresh protocol snapshot from routine teardown so `serve`/`connect` clients stop seeing completed routines as still active.
- Hardened `_cancel_active_routine()` so stale or already-finished routines log cleanly instead of throwing `'NoneType' object has no attribute 'cancel'`.
- Added regression coverage for stale routine cancellation and teardown snapshot publication, then reran focused control-room tests plus the full suite.

## Follow-ups

- Live-validate the dock/undock and haul completion path over a real remote session to confirm the client prompt state now clears immediately after completion.
