# Iteration Log

- Area: `web`
- Title: `haul-page-static-prototype`
- Started: `2026-07-04 07:46`

## Summary

- Added a static HTML-only prototype for the v1 web Haul page, using the external component library's restrained dark/amber design language while keeping the layout purpose-built for EDControlRoom's two-way haul workflow.

## Changes

- Created `web/haul-v1.html` with no backend integration or build step.
- Included route search, route results, selected-route setup, command preview, routine summary, and activity sample sections.
- Added explicit station/carrier-only guardrails in both search and start panels; the preview always emits `station_1_on_land=false` and `station_2_on_land=false`.
- Reflected the agreed v1 scope: two-way haul only, no prompt flow, no Inara URL import, and no market page.

## Follow-ups

- Add backend support for server-owned haul search data in hydrate plus a structured search command before wiring this page to live data.
- Keep route row selection browser-local; use structured `command.dispatch_haul_loop` only when the operator starts a selected route.
