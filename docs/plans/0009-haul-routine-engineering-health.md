# 0009: Haul Routine Engineering Health

## Status

Implemented.

## Why

The haul routines have accumulated too many responsibilities in too few files. `haul_two_way.py` owns journal reads, cargo predicates, start-phase detection, market operations, galaxy-map routing, station departure, transit resume logic, docking handoff, loop orchestration, defaults, and the public routine API. `haul_multi_leg.py` repeats several of those mechanics and imports private helpers from two-way haul.

This makes every new operational knob widen function signatures, context objects, Control Room dispatch code, CLI dispatch code, and tests.

## Target Shape

- Two-way and multi-leg haul keep their current runtime behavior.
- Shared haul mechanics live in shared haul routine modules, not as private two-way helpers.
- Route-specific modules own only route-specific state detection and phase orchestration.
- Runtime dependencies, timing settings, market settings, and travel settings are grouped into small typed objects.
- Routine entrypoints and internal phases consume grouped settings instead of long lists of timing/config keyword arguments.
- Manual CLI and Control Room dispatch stay aligned with the routine API.

## Refactor Sequence

### 1. Shared haul primitives

Extract shared journal/cargo readers, transit resume detection, arrival waits, manual landing results, galaxy-map retry behavior, navigation-panel opening, and hyperspace engage helpers into shared haul routine modules.

### 2. Group routine context

Replace large route-specific context objects with a small route context plus shared runtime/config objects.

### 3. Split route-specific responsibilities

Keep two-way-specific station leg and phase detection in two-way modules, and multi-leg-specific stop/phase handling in multi-leg modules. Do not make either route import private helpers from the other.

### 4. Shorten dispatch APIs

Move Control Room and manual CLI dispatch to grouped route/runtime objects so new timing or market knobs do not expand every routine call site.

### 5. Rebalance tests

Keep behavior coverage, but split very large haul test files once the production modules have stable boundaries.

## Acceptance Criteria

- `haul_two_way.py` no longer owns shared multi-leg mechanics.
- `haul_multi_leg.py` no longer imports private helpers from `haul_two_way.py`.
- The main haul context is no longer a long flat list of dependencies and timing knobs.
- Control Room and manual CLI dispatch both call the current routine API successfully.
- Existing haul behavior tests pass under `uv run python3 -m unittest discover -s tests`.

## Non-Goals

- No UI/UX changes.
- No behavioral retuning of haul, docking, market, or galaxy-map automation.
- No live-game assumptions added without operator validation.
