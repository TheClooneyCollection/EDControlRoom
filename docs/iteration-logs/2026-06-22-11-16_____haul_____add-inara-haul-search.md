# Iteration Log

- Area: `haul`
- Title: `add-inara-haul-search`
- Started: `2026-06-22 11:16`

## Summary

- Added the first real `haul search [system]` path so Control Room can fetch live Inara trade routes headlessly and keep the results visible in a dedicated panel.

## Changes

- Extracted the Playwright-backed Inara route fetch and row parsing into `edap/inara/trade_routes.py`, with the scratch probe slimmed down into a wrapper over that shared module.
- Added a local `TradeRoutesData` state model plus a `TRADE ROUTES` panel in Control Room, rendered independently from the existing market and haul panels.
- Extended `haul` command handling so `haul search [system]` records history, defaults to the current ship system when omitted, skips the bindings/controls prerequisite, and updates the panel with loading, success, or failure state.
- Updated haul help text and the command placeholder to advertise `haul search [system]`.
- Added unit coverage for the shared Inara helpers, the new panel rendering, and the `haul search` command flow.
- Verified the shared scratch probe still fetches the live Inara DOM after the refactor and re-ran the full suite successfully.

## Follow-ups

- Decide whether Inara route state should remain local-only or be promoted into the remote observer snapshot/wire contract.
- Decide whether the current operator-supplied Inara query defaults should move into explicit config once the route panel ergonomics settle.
