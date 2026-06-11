# Iteration Log

- Area: `docs`
- Title: `status-split-and-promotion-automation`
- Started: `2026-06-11 13:45`

## Summary

- Replaced the shared `docs/STATUS.md` handoff with split area status files under `docs/status/`, kept iteration logs as the chronological layer, and added a dedicated `dev -> main` promotion workflow branch that carries generated iteration-archive updates instead of pushing them directly onto `dev`.

## Changes

- Added `docs/status/README.md` plus durable area status files and per-area archive files, then removed the old top-level `docs/STATUS.md`.
- Updated `AGENTS.md`, `README.md`, `docs/README.md`, and the docs-planning references to point at the new status entrypoint and the new trimming/archive rules.
- Added `.github/workflows/promote-dev-to-main.yml` so `promote-dev-to-main--generated-iteration-archive` is rebuilt from `dev`, refreshed with the generated `docs/iteration-archive.md`, and used as the standing promotion PR head branch.

## Follow-ups

- Live-check the promotion workflow once merged by confirming the branch recreation, PR refresh, and token/CI behavior on GitHub.
- Watch a few real sessions to see whether any status area should be split further or collapsed back together.
