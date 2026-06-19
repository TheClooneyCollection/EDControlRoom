# Iteration Log

- Area: `docs`
- Title: `regenerate-iteration-archive-conflicts`
- Started: `2026-06-19 11:49`

## Summary

- Added an explicit repo rule that `docs/iteration-archive.md` must be regenerated, not hand-merged, whenever it conflicts during a merge or rebase.
- Applied that rule while rebasing `codex/control-room-remote-followup` onto the latest `origin/main`, which avoided repeated manual conflict resolution on the generated archive.

## Changes

- Updated `AGENTS.md` to require `uv run python3 tools/iteration_logs.py render-archive` plus staging the regenerated file whenever the archive conflicts.
- Updated `docs/status/docs-process.md` so the current handoff reflects the same generated-file conflict policy for future agents.

## Follow-ups

- Keep using regeneration for future archive conflicts and treat any hand-merged archive content as suspect until re-rendered from `docs/iteration-logs/`.
