# Iteration Log

- Area: `docs`
- Title: `iteration-log-validation-workflow`
- Started: `2026-06-12 10:18`

## Summary

- Added explicit iteration-log filename validation and documented the required `new` plus `validate` workflow in repo handoff instructions.

## Changes

- Added `validate_iteration_logs()` in `edap/iteration_logs.py` and a `validate` subcommand in `tools/iteration_logs.py`.
- Renamed the malformed `haul` iteration logs so they match the padded-area filename contract and no longer break archive generation.
- Updated `AGENTS.md`, `docs/iteration-logs/README.md`, and `docs/status/docs-process.md` to require tool-driven log creation and pre-commit/pre-PR validation.

## Follow-ups

- Consider wiring `uv run python3 tools/iteration_logs.py validate` into any future docs or PR-readiness automation so the rule is enforced mechanically.
