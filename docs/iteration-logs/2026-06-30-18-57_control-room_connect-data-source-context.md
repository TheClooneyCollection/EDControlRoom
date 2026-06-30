# Iteration Log

- Area: `control-room`
- Title: `connect-data-source-context`
- Started: `2026-06-30 18:57`

## Summary

- Moved more connect-mode command context reads from legacy view snapshot state to the remote data source.

## Changes

- `ObserverControlRoomApp` now keeps an optional remote data source reference for production connect mode.
- Active-operator gating for routine readiness and command input refresh reads `data_source.session.client_role` when available.
- Local command ship context and trade-search system lookup read `data_source.ship` when available.
- Commander-name initialization uses hydrated ship data when available.

## Follow-ups

- Continue moving remaining command bar, replay browser, and trade-route picker state away from internal snapshot compatibility.
