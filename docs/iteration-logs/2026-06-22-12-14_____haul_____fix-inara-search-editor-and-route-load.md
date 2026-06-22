# Iteration Log

- Area: `haul`
- Title: `fix-inara-search-editor-and-route-load`
- Started: `2026-06-22 12:14`

## Summary

- Corrected the first Inara search UX pass so search parameters are edited all at once, ship cargo capacity actually defaults into the editor, and returned routes can now be loaded into the haul prompt.

## Changes

- Replaced the sequential search question flow with a single prefilled `key=value` editor line backed by the same prompt-state machinery, removing the duplicated `min_supply` step bug and making every search field visible at once.
- Extended route parsing to retain the source buy commodity and optional return-leg buy commodity, then surfaced those fields in the `TRADE ROUTES` panel.
- Added `haul route <n>` so operators can load a shown Inara result into the haul prompt with station names, systems, and cargo defaults prefilled for review before launch.
- Expanded tests for all-at-once search editing, ship cargo defaulting, route-to-haul loading, and commodity extraction from route cards.

## Follow-ups

- Live-validate the `haul route <n>` commodity mapping against a few real one-way and round-trip Inara cards, especially rows where the site layout or labels differ from the sample shapes used in tests.
