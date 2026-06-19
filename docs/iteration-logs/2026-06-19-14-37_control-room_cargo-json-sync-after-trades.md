# Iteration Log

- Area: `control-room`
- Title: `cargo-json-sync-after-trades`
- Started: `2026-06-19 14:37`

## Summary

- Made post-trade cargo state authoritative from `Cargo.json` instead of trusting the app's in-memory manifest after market journal events.

## Changes

- Added `bootstrap.sync_cargo_manifest()` and wired `_handle_event()` to re-read `Cargo.json` after `Cargo`, `MarketBuy`, and `MarketSell`.
- Kept bootstrap startup behavior aligned with existing expectations by leaving startup `cargo_count` sourced from `Status.json` while still loading manifest contents from `Cargo.json`.
- Added control-room regression tests covering full-sell stale manifest cleanup plus manifest refresh after both market buys and sells.

## Follow-ups

- Live-test repeated remote and local `sell`/`buy` flows against real journal timing to confirm `Cargo.json` is always updated before the follow-up command path re-checks inventory.
