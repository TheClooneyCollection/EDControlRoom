# 0006: Repo Cleanup and Product Positioning

## Status

Implemented on 2026-06-07, with screenshot asset follow-up still open

## Priority

High

## Why

The repo currently mixes active macOS-first runtime surfaces with legacy Windows-era reference code, ad hoc scratch probes, and a README that is carrying too much low-level operational detail.

That makes three things harder than they should be:

- understanding the current product surface at a glance
- identifying which files are active versus historical reference
- keeping the repo root and README aligned with the real operator workflow

The current project story is now strong enough to simplify around it:

- primary target: macOS
- live game runtime: Elite Dangerous through CrossOver
- primary operator surface: `control_room.py`
- strongest current routine: `haul`, alongside `dock`, `undock`, `jump`, `buy`, `sell`, and `dest`

## Goals

- Make the macOS-first / CrossOver-compatible positioning explicit in the first screenful of the repo.
- Make `control_room.py` the obvious primary entrypoint.
- Remove legacy/reference code from the active repo root without losing it.
- Move low-level utility and diagnostics documentation out of `README.md` into focused docs pages.
- Group scratch/probe scripts so the root reflects supported entrypoints rather than experiments.
- Reduce repo-root ambiguity for future agents and contributors.

## Non-Goals

- No functional behavior changes to routines or platform adapters.
- No rewrite of the actual routine stack as part of this cleanup.
- No deletion of historical reference code; it should be archived, not discarded.

## Proposed Structure

### 1. README reset

Rebuild `README.md` around the current product story:

- short project description
- explicit macOS-first / CrossOver-compatible statement near the top
- Control Room screenshot
- concise “what works today” section
- primary entrypoints
- routine overview, highlighting `haul`
- docs map linking deeper operational pages
- link to `docs/status/README.md` for maintained status

Move detailed utility usage, diagnostics detail, and scratch-script detail out of the README.

### 2. Archive legacy code

Move Windows-era / superseded reference surfaces into an archive area, for example:

- `archive/legacy-windows/autopilot.py`
- `archive/legacy-windows/dev_autopilot.py`
- `archive/legacy-windows/dev_autopilot.ipynb`
- `archive/legacy-windows/dev_tray.py`
- `archive/legacy-windows/src/directinput.py`

Add an archive README explaining that these files are historical behavior references, not active architecture.

### 3. Split documentation by purpose

Introduce clearer docs groupings:

- `docs/getting-started/`
- `docs/operators/`
- `docs/diagnostics/`
- `docs/assets/`

Keep `docs/status/` as the maintained status surface, and keep `docs/plans/`, `docs/research/`, `docs/design/`, and `docs/devlog/` for deeper material.

### 4. Group scratch and probe scripts

Move exploratory scripts out of the root into a dedicated tools area, likely:

- `tools/scratch/`

Candidates:

- `tools/scratch/scratch_cgevent.py`
- `tools/scratch/scratch_cv.py`
- `tools/scratch/scratch_market.py`
- `tools/scratch/scratch_rebake.py`

If needed later, split “supported developer tools” and “exploratory probes” into `tools/diagnostics/` and `tools/scratch/`.

### 5. Promote Control Room

Add the provided screenshot as a tracked asset, likely:

- `docs/assets/control-room.png`

Use it in the README and frame Control Room as the main operator experience:

- live ship status
- activity log
- market panel
- routine dispatch
- cross-session replay/history
- saved default haul setup

### 6. Repo-root hygiene

Aim for a top-level layout that mostly contains:

- active entrypoints
- `edap/`
- `docs/`
- `tests/`
- `tools/`
- `archive/`
- config/build metadata

The root should communicate “current runtime surface” rather than “full history of experiments.”

## Suggested File Moves

### Active root entrypoints to keep

- `control_room.py`
- `run_routine.py`
- `diagnostics.py`
- `ship_controls.py`
- `check_bindings.py`
- `watch_journal.py`
- `set_binding.py`
- `view_bindings.py`

### Legacy/reference candidates to archive

- `autopilot.py`
- `dev_autopilot.py`
- `dev_autopilot.ipynb`
- `dev_tray.py`
- `src/directinput.py`

### Scratch/probe candidates to move

- `tools/scratch/scratch_cgevent.py`
- `tools/scratch/scratch_cv.py`
- `tools/scratch/scratch_market.py`
- `tools/scratch/scratch_rebake.py`

## Recommended Execution Order

1. Standardize product naming and macOS-first positioning.
2. Rewrite `README.md` around Control Room and current operator workflows.
3. Add the Control Room screenshot and a docs index.
4. Move legacy code into `archive/legacy-windows/`.
5. Move scratch/probe scripts into `tools/scratch/`.
6. Split low-level utility and diagnostics docs out of `README.md`.
7. Update `docs/status/README.md` and the relevant area files to reflect the new layout and entrypoints.

## Acceptance Criteria

- The top of `README.md` makes macOS compatibility and CrossOver support explicit.
- The README is materially shorter and links to deeper docs instead of embedding everything.
- Legacy Windows-era files are out of the active root and clearly labeled as archived.
- Scratch/probe scripts are grouped into a non-root tools area.
- The Control Room screenshot is included in the docs/README path.
- Future contributors can tell the difference between:
  - active runtime entrypoints
  - supported developer/operator tools
  - archived historical reference code
  - experimental scratch probes

## Notes For The Next Agent

- Treat this as a repo-shape and product-positioning pass, not a behavior refactor.
- Keep moves incremental and reviewable; avoid mixing broad file motion with unrelated code changes.
- Update docs links carefully after each move so the cleanup does not leave broken navigation behind.
