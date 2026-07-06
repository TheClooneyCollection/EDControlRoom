# Iteration Log

- Area: `haul`
- Title: `sell-unrelated-cargo-before-buy`
- Started: `2026-07-06 20:46`

## Summary

- Changed the two-way haul pre-buy non-haul cargo path from an immediate abort into an announced sell-all recovery attempt followed by the intended buy.

## Changes

- Added `haul_unrelated_cargo_loaded` and `selling_all_cargo` announcement IDs plus default TTS phrases.
- Added a bounded pre-buy cleanup helper that sells every sellable Cargo.json item once, waits the configured post-sell settle delay, verifies non-haul cargo cleared, and only then retries the planned buy.
- Kept stale/unknown cargo details as an abort path because the routine still cannot safely identify what to sell from an empty or stale manifest.
- Updated haul/config unit coverage for the new announcements and sell-before-buy recovery path.

## Follow-ups

- Live-validate recovery against real Cargo.json/Market.json timing; future TUI/web UX should prompt for confirmation with the cargo list before auto-selling.
