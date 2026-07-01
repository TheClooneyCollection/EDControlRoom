# Iteration Log

- Area: `haul`
- Title: `supercruise-empty-hold-phase-detection`
- Started: `2026-07-01 12:24`

## Summary

- Fixed two-way haul startup phase detection for the live case where the commander starts `haul` in supercruise in station 1/2's system with an empty hold and a buy commodity configured for that local station.

## Changes

- Updated `_detect_start_phase()` so empty-hold supercruise in the local buy station system returns to that station's transit/dock phase instead of assuming outbound transit to the opposite station.
- Added regression coverage for station 1 and station 2 empty-hold supercruise starts, plus the one-sided route case where a blank local buy commodity should still continue to the opposite station.
- Verified `uv run python3 -m unittest tests/test_haul_two_way.py` and `uv run python3 -m unittest discover -s tests` (`617` tests, `0.314s`).

## Follow-ups

- Live-validate the normal-space empty-hold resume case separately before changing it, because that branch currently overlaps with launch/escape resume behavior.
