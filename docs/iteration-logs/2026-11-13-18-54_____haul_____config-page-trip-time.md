# Iteration Log

- Area: `haul`
- Title: `config-page-trip-time`
- Started: `2026-11-13 18:54`

## Summary

- Built step 4 of [plan 0016](../plans/0016-journal-events-and-trip-time-fit.md): a `/config` page whose Trip time section shows the configured and fitted values side by side, lets the player edit the configured ones, switch between the two sets and save them into `config.toml`, live.

## Changes

- `web/config.html` and `web/config.js`, with a sidebar entry under **Setup** (`nav.js`) and `config.js` in the asset allowlist. Per field: the configured value (editable), the fitted value or `configured` when too few legs fit it, and its supporting legs. Under the table: which ship the fit is for, legs, docked stops and window, and a 1-jump 300 Ls leg under both sets.
- `POST /api/time-model` takes `{source, configured: {field: value}}`; fields left out stay. It writes `[eddn.time_model]` with `save_time_model` (`edcr/config.py`, the same line upsert as the home system) and calls `TripTimeModels.set_configured`, so the next route search uses it. Bad source, unknown field, negative or non-number values get 400.
- Only the server that keeps the journal events saves: a peer answers 409 and its GET carries `"hub"` and `"editable": false`. A server running on `config.example.toml` (no `config.toml`) answers 503 rather than writing into the example.
- `/routes` status and Best deal's per-hour note name the set used: configured, fitted for this ship, fitted on every ship, or configured because there were too few legs.
- Checked in a scratch server on the live store with playwright at 1200 and 390 px; the first run caught `config.js` missing from the asset allowlist, now covered by a test.

## Follow-ups

- Step 5: docs pass (`docs/user/hub.md`, README if the page list is there).
- Live: restart the hub and open `/config`; forge still to link.
