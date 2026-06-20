# Docs Process Status
## Current
- Only `control_room.py` now stays at the repo root; auxiliary operator and validation CLIs live under `tools/`, while `tools/scratch/` remains the exploratory bucket.
- `AGENTS.md` now treats `docs/iteration-archive.md` as fully generated during rebases and merges: if it conflicts, regenerate it with `uv run python3 tools/iteration_logs.py render-archive` and stage the regenerated file instead of hand-resolving conflict markers.
- `AGENTS.md` now treats `0.3s` as the full-suite runtime budget for `uv run python3 -m unittest discover -s tests`; only slower runs need the follow-up timing report.
- `AGENTS.md` now requires `docs/iteration-archive.md` refresh whenever iteration logs change before commit/push/PR, and delegated-agent slices must be committed on their own branch before a parent push or PR depends on them.
- The repo now ships as rolling updates on `main`; do not assume a long-lived `dev` branch or promotion PR path in docs/process guidance.
- Iteration logs should now be created with `uv run python3 tools/iteration_logs.py new "<area>" "<title>"` and validated with `uv run python3 tools/iteration_logs.py validate` before commits, pushes, and PRs so malformed filenames do not break archive generation.
- PR validation now renders `docs/iteration-archive.md` and fails if the generated file differs, so iteration-log changes must include a local archive refresh before review.
- Delegated-agent workflow now requires one branch and one git worktree per agent slice so concurrent work stays isolated from the main checkout.
- Maintained current-state handoff now lives in `docs/status/*.md` instead of a single shared `docs/STATUS.md`.
- Per-iteration notes live in `docs/iteration-logs/`, and `docs/iteration-archive.md` is generated rather than manually maintained.
- Legacy global handoff history remains in `docs/status-archive.md`; new displaced area-status history belongs in `docs/status/archive/*.md`.
## Caveats
- Archive generation still depends on every iteration log matching the exact filename contract, so malformed manual renames remain a hard failure until validation is run.
- Agent slices are isolated in worktrees, but the parent checkout still needs to confirm every delegated slice was verified and committed before publishing combined work.
- Rolling updates on `main` reduce branch-management overhead, but the docs need clear known-issues and feature-completeness notes so tagged stable states remain easy to distinguish from in-progress work.
## Next
- Keep historical iteration logs as-is for chronology, but keep current docs and automation free of stale `dev -> main` guidance or stale archive-refresh instructions.
- Trim or merge area files aggressively if any start drifting toward branch-by-branch narrative instead of current truth.
