# Docs Process Status
## Current
- Delegated-agent workflow now requires one branch and one git worktree per agent slice so concurrent work stays isolated from the main checkout.
- Maintained current-state handoff now lives in `docs/status/*.md` instead of a single shared `docs/STATUS.md`.
- Per-iteration notes live in `docs/iteration-logs/`, and `docs/iteration-archive.md` is generated rather than manually maintained.
- Legacy global handoff history remains in `docs/status-archive.md`; new displaced area-status history belongs in `docs/status/archive/*.md`.
## Caveats
- The new split status workflow still needs a few sessions of real use to confirm the area boundaries are right.
## Next
- Trim or merge area files aggressively if any start drifting toward branch-by-branch narrative instead of current truth.
