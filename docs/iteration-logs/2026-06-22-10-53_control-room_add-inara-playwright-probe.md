# Iteration Log

- Area: `control-room`
- Title: `add-inara-playwright-probe`
- Started: `2026-06-22 10:53`

## Summary

- Added a scratch Playwright probe that can open a live Inara trade-routes page, wait for the route cards to render, and print compact summaries from the real DOM.

## Changes

- Added `tools/scratch/scratch_inara_trade_routes.py` with a persistent Playwright browser profile, timeout handling for Inara's access-check interstitial, optional HTML/JSON/screenshot capture, and compact route summary output.
- Kept the probe outside the main runtime surface by placing it under `tools/scratch/` and by importing Playwright lazily with an explicit install hint if the optional `browsing` extra is missing.
- Added unit coverage for the probe's inline text parsing and endpoint cleanup in `tests/test_scratch_inara_trade_routes.py`.
- Updated `tools/scratch/README.md` and `docs/diagnostics/cli-reference.md` to advertise the new probe.
- Verified a live headless run against the provided Inara traderoutes URL; the probe loaded 50 `div.mainblock.traderoutebox` rows and printed route/profit summaries, confirming Playwright can reach the real results DOM where plain HTTP fetches were challenged.

## Follow-ups

- Move the route extraction from scratch-script dicts into typed parser/model code once the exact Control Room presentation shape is chosen.
- Decide whether the first Control Room integration should read saved probe JSON, call the probe subprocess, or share the Playwright extraction logic directly.
