# Iteration Log

- Area: `haul`
- Title: `guard-unrelated-preloaded-cargo`
- Started: `2026-07-06 12:12`

## Summary

- Fixed the two-way haul bug where pre-existing cargo unrelated to the configured haul leg could be treated as wrong-buy recovery cargo and sold automatically.

## Changes

- Added a pre-buy guard in `edap/routines/haul_two_way.py` that aborts before market input when `Cargo.json` already contains positive-count cargo that does not match the current leg's expected buy commodity.
- The abort tells the operator to clear or sell the non-haul cargo manually, emits the generic haul-aborted announcement, and preserves the existing stale-cargo guard for the separate `Status.json` cargo / empty `Cargo.json` case.
- Added regression coverage for unrelated preloaded cargo, for partially loaded expected cargo continuing into buy, and adjusted existing sell mocks so successful fake sells clear cargo state.
- Verified `uv run python3 -m unittest tests/test_haul_two_way.py` and the full suite `uv run python3 -m unittest discover -s tests` passed; full suite reported `689 tests in 0.406s`.

## Follow-ups

- Live-check the abort wording in a real haul resume/start flow with unrelated cargo aboard to confirm the operator-facing message is clear enough before adding a more specific TTS phrase.
