# Iteration Log

- Area: `web`
- Title: `web-config-injection`
- Started: `2026-07-06 10:14`

## Summary

- Removed environment/demo assumptions from the haul web HTML by moving server, auth, role, target, and form-default data into an injected `window.EDCR_WEB_CONFIG` payload.

## Changes

- Added input-target summary and web form defaults to the Control Room data read model so the server can expose runtime-aware web defaults.
- Updated `/`, `/haul`, and `/multi-haul` rendering to inject host/auth/runtime/default config from the current server data provider instead of only replacing a token string.
- Neutralized static haul HTML values for host, target, role, cargo, runs, profit, and route parameters; browser JS now applies defaults and reset values from the injected config plus hydrate/ship data.
- Cleared stale localhost/token defaults from the scratch remote browser probe.

## Follow-ups

- Consider adding a richer web defaults model if multi-leg planning gains backend-owned settings beyond the current route-search and haul timing defaults.
