# Iteration Log

- Area: `haul`
- Title: `interdiction-docking-abort`
- Started: `2026-07-04 21:49`

## Summary

- Reviewed `artifacts/control-room.log` and confirmed live interdiction sequences where `Interdicted` is followed by `SupercruiseExit` on a star/planet plus `Combat_Dogfight`, distinct from later station `SupercruiseDestinationDrop` events.

## Changes

- Added an opt-in `dock(abort_on_interdiction=True)` guard and enabled it for two-way and multi-leg haul transit so haul aborts/TTS `haul_aborted` before any docking request when interdicted during station approach.
- Added regression coverage for two-way and multi-leg haul using the logged event shape: destination-system `FSDJump`, `Interdicted`, then non-station `SupercruiseExit`.

## Follow-ups

- Watch future live haul logs for interdiction variants that emit only emergency-drop style events without `Interdicted`; current guard keys on the explicit journal event seen in artifacts.
