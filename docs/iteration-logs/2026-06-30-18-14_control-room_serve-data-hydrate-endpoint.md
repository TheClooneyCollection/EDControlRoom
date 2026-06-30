# Iteration Log

- Area: `control-room`
- Title: `serve-data-hydrate-endpoint`
- Started: `2026-06-30 18:14`

## Summary

- Added the first server route for the no-snapshot data protocol.

## Changes

- Added authenticated `GET /hydrate` to the observer server app.
- Wired `control_room serve` to serve hydrate data from `runtime_host.dependencies.data_source.current`.
- Added server tests covering `control_room.hydrate` payload shape and UI-state omission.

## Follow-ups

- Add websocket hydrate/update streaming for remote data sources.
- Rebuild `connect` around remote data-source hydration instead of `/snapshot`.
