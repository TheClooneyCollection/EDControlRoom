# Iteration Log

- Area: `control-room`
- Title: `add-optional-playwright-extra`
- Started: `2026-06-22 10:42`

## Summary

- Added an optional Playwright-based browsing dependency path so Inara route work can use a real browser without changing the default install set for normal users.

## Changes

- Added a `browsing` extra in `pyproject.toml` with `playwright>=1.53` instead of placing Playwright in base dependencies or the existing `dev` extra.
- Refreshed `uv.lock`; the optional extra resolved to `playwright`, `greenlet`, and `pyee`.
- Confirmed the current Inara assumption for this environment: direct HTTP requests still hit the access-check interstitial even with copied authenticated cookies, so the live route prototype should start from browser-backed DOM acquisition.
- Re-ran the full unittest suite after the packaging change; `519` tests passed in `0.286s`.

## Follow-ups

- Install the extra explicitly with `uv sync --extra browsing` only on machines that need the browser-backed route probe.
- After that install, add a headed Playwright probe that opens the Inara traderoutes page, waits for `div.mainblock.traderoutebox`, and prints a compact parsed summary.
