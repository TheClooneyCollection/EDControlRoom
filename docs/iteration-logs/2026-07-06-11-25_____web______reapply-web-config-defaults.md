# Iteration Log

- Area: `web`
- Title: `reapply-web-config-defaults`
- Started: `2026-07-06 11:25`

## Summary

- Reapplied the injected web-config/defaults cleanup after the two-way haul UI restore split `/haul` and `/multi-haul` into separate web pages.

## Changes

- Removed restored machine/process/demo literals from the two-way haul page while preserving its route-table UI.
- Routed two-way route search, haul timing defaults, websocket auth query naming, and session/status labels through `window.EDCR_WEB_CONFIG` again.
- Applied the same neutral static defaults and config-driven reset behavior to the new standalone multi-haul page.
- Removed the legacy `EDCR_SERVER_DEFAULT_ACCESS_TOKEN` fallback path from the served web templates and renderer.
- Added a regression test to prevent runtime-specific demo defaults from returning to the web pages.

## Follow-ups

- Keep future web UI restores on top of the injected config contract instead of reintroducing page-local runtime defaults.
