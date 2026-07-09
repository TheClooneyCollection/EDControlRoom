# Iteration Log

- Area: `control-room`
- Title: `direct-dock-normal-space`
- Started: `2026-07-09 12:35`

## Summary

- Fixed direct `dock` so it waits for `SupercruiseExit` only when Control Room state says the ship is in supercruise.

## Changes

- Added an explicit direct-command predicate in `edap/control_room/routines_station.py`; normal space now skips the drop wait and starts docking attempts immediately.
- Added Control Room regression coverage for supercruise wait behavior and normal-space immediate docking.
- Documented the current direct-command vs transit-wrapper station routine split in `docs/devlog/0003-station-routine-split.md`.

## Follow-ups

- Consider moving shared station command policy into a neutral helper if direct station commands and transit wrappers continue to accumulate parallel state decisions.
