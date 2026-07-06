# Iteration Log

- Area: `haul`
- Title: `persist-haul-search-defaults`
- Started: `2026-07-06 21:04`

## Summary

- Saved edited haul-search parameters back to the ignored repo-local `haul_search.toml` so changes like route distance and station distance become future defaults.

## Changes

- Added `save_haul_search_config()` with TOML section upsert support and a generated-field exclusion list that currently keeps journal-derived `cargo_capacity` out of automatic saves.
- Wired Textual `haul search`, pasted Inara URL dispatch, and web/server `command.search_haul_routes` to save cleaned search defaults before running the search.
- Added regression coverage for the config writer plus Textual/server search save calls without writing to the real ignored config during tests.

## Follow-ups

- Live-check that web `/haul` route-distance edits are reflected after a page refresh/reconnect during the next operator session.
