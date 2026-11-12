# Iteration Log

- Area: `control-room`
- Title: `global-routes-distance`
- Started: `2026-11-12 17:35`

## Summary

- `/routes` Global view now shows how far each station is from the current system. The station-to-station Ly was already under the Jumps column in both views, so the new number is distance from the commander.

## Changes

- `run_route_query` looks up the query system's coordinates in both views; Near still errors when missing, Global carries on without distances. Only Near passes the origin to `find_routes` as a filter.
- Each station in the payload gains `ly_from_system`; the payload gains `distance_system` (null when there are no coordinates).
- `web/routes.js` adds `<n> Ly away` to each station's sub line (Near too, since the origin is known there) and names the system in the status line.
- On a hub, the peer's `resolve_route_params` already fills `system` with the peer's current system, so distances are from the peer's ship.

## Follow-ups

- Not tried in a browser or live session.
