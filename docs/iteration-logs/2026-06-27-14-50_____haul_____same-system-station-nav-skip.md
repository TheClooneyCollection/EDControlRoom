# Iteration Log

- Area: `haul`
- Title: `same-system-station-nav-skip`
- Started: `2026-06-27 14:50`

## Summary

- Fixed the two-way haul same-system edge case so station-to-station loops inside one system no longer try to re-set a galaxy-map destination before transit.

## Changes

- Added a same-system guard in `edap/routines/haul_two_way.py` so both undock-driven and normal-space depart paths skip `set_gal_map_destination()` when the source and destination systems match.
- Added two haul regressions covering the undock path and the resumed normal-space depart path for same-system station pairs.
- Verified `uv run python3 -m unittest tests/test_haul_two_way.py` passed, then ran the full suite successfully at `547 tests in 0.339s`.

## Follow-ups

- Full-suite runtime exceeded the repo target, so `tools/report_test_timing.py --top 10 --sort slowest` was run per policy; current timing report came back `suite_status=ok` with `total_seconds=0.315`.
