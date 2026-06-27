# Iteration Log

- Area: `control-room`
- Title: `bootstrap-cargo-capacity-for-haul-search`
- Started: `2026-06-27 18:20`

## Summary

- Fixed the restart-time gap where Control Room bootstrapped cargo count from `Status.json` but dropped total cargo capacity from the latest journal, causing `haul search` prefills to omit `cargo_capacity=` until a fresh live `Loadout` arrived.

## Changes

- Extended `edap.state.read_ship_state()` to retain `Loadout.CargoCapacity` in the lightweight journal bootstrap state.
- Updated Control Room bootstrap to copy that restored `cargo_capacity` onto the live ship model before haul-search defaults are generated.
- Expanded the bootstrap ship-state test to include a `Loadout` event and assert that cargo capacity survives startup alongside the `Status.json` cargo count.

## Follow-ups

- Keep `artifacts/control-room-debug.log` in place while live Inara behavior is still being validated, but the missing `cargo_capacity` root cause for blank search prefills is now covered by startup bootstrap and test coverage.
