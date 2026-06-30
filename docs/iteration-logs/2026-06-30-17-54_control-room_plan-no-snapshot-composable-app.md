# Iteration Log

- Area: `control-room`
- Title: `plan-no-snapshot-composable-app`
- Started: `2026-06-30 17:54`

## Summary

- Captured the replacement Control Room architecture: one local-first app composed with data sources, view models, view actions, and execution dependencies.

## Changes

- Added `docs/plans/0008-control-room-composable-app-refactor.md` with the no-snapshot target architecture, ownership rules, protocol direction, refactor sequence, and acceptance criteria.
- Marked the older snapshot-based client/server refactor plan as superseded by plan 0008.

## Follow-ups

- Start implementation bottom-up by introducing dependency protocols and local wiring before replacing remote `serve` / `connect`.
