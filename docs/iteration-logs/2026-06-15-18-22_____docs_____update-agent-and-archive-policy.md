# Iteration Log

- Area: `docs`
- Title: `update-agent-and-archive-policy`
- Started: `2026-06-15 18:22`

## Summary

- Updated repo policy to treat `docs/iteration-archive.md` as a required refreshed artifact whenever iteration logs change before commit/push/PR, and tightened delegated-agent publish rules so slices must be committed before parent push/PR.

## Changes

- Corrected the stale `AGENTS.md` guidance that still described iteration archive refresh as optional/manual-only.
- Added explicit delegated-agent requirements in `AGENTS.md` for commit-before-publish and archive refresh before any push or PR that includes iteration-log changes.
- Updated `docs/status/docs-process.md` so the maintained handoff matches the new docs/archive and agent-publish workflow.

## Follow-ups

- Keep the workflow docs aligned with CI behavior whenever archive generation or delegated-agent publish rules change again.
