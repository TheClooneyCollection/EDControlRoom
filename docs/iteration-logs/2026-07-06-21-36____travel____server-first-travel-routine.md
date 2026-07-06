# Iteration Log

- Area: `travel`
- Title: `server-first-travel-routine`
- Started: `2026-07-06 21:36`

## Summary

- Added the first server-first `travel` routine for assistive anywhere-to-station travel, with TUI, remote client, websocket protocol, and web `/haul` surface access.
- Extracted shared station transit behavior out of haul-specific code into a neutral routines module so two-way haul, multi-leg haul, and travel use the same launch/route/transit/docking path.
- Added selected-route shortcuts so TUI search results can save a route, travel to its first station with `t`, and start the selected/saved haul with `haul start`.

## Changes

- Added `edap.routines.transit` for shared ship-position reads, route-needed detection, route retry/unconfirmed-route handling, undock/depart helpers, in-system nav-panel presentation, manual landing handoff, and station docking transit.
- Added `edap.routines.travel.travel_to_station` and `travel <system> / <station>` command dispatch.
- Added structured `command.dispatch_travel` protocol support across capabilities, schema, server handler, local/remote execution dependencies, and client backend delegation.
- Added a compact Travel Assist form to the existing `/haul` web page that sends `command.dispatch_travel`.
- Updated the `/haul` web selected-route behavior so the Travel Assist target system/station follows the selected route's first station.
- Updated haul and multi-leg haul to call shared transit helpers instead of local duplicate transit code.
- Added unit coverage for travel same-system nav-panel behavior, docked-start shared transit reuse, websocket dispatch, remote backend dispatch, TUI route shortcuts, `haul start`, and web surfacing.

## Follow-ups

- Live-validate `travel` under CrossOver/macOS from docked, normal-space, same-system supercruise, and remote-system starts.
- Decide whether Travel Assist deserves a dedicated `/travel` web page after live behavior stabilizes.
