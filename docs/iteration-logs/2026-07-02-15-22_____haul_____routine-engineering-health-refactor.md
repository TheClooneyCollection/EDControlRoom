# Iteration Log

- Area: `haul`
- Title: `routine-engineering-health-refactor`
- Started: `2026-07-02 15:22`

## Summary

- Refactored haul routine internals so shared two-way/multi-leg mechanics live outside `haul_two_way.py`.

## Changes

- Added `edap.routines.haul_support` for shared cargo/journal readers, transit resume detection, arrival/on-land waits, manual landing results, galaxy-map retry, nav-panel opening, hyperspace engage, and grouped runtime/settings objects.
- Collapsed two-way and multi-leg route contexts around `HaulRuntime` plus route-specific legs/stops, instead of long flat bags of controls, callbacks, timers, and market settings.
- Removed the long public two-way and multi-leg haul signatures; Control Room and the manual CLI now pass `HaulRuntime` plus route/definition objects.
- Removed multi-leg imports of private two-way helpers and updated tests to patch the new shared galaxy-map helper owner.
- Fixed stale manual CLI routine wiring to pass current market hold segment config and explicit announcement callbacks.

## Follow-ups

- Split very large haul behavior test files once the new production module boundaries have settled.
