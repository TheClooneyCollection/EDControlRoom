# Iteration Log

- Area: `ci`
- Title: `promote-playwright-runtime-dependency`
- Started: `2026-06-27 19:07`

## Summary

- Promoted `playwright` from the optional `browsing` extra into the base project dependency list so released installs include the browser dependency by default.

## Changes

- Updated `pyproject.toml` to add `playwright>=1.53` to `[project].dependencies` and removed the now-obsolete `browsing` extra entry.
- Refreshed `uv.lock` so the locked project metadata now advertises Playwright as a normal runtime dependency instead of an extra-gated dependency.
- Updated `docs/status/ci-release.md` so the current release handoff reflects that published installs no longer require a separate Playwright extra.

## Follow-ups

- Keep future install docs and release notes aligned with the new default dependency shape; do not reintroduce a browser-only extra unless the runtime surface changes again.
