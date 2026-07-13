# Iteration Log

- Area: `travel`
- Title: `neutron-travel-routine`
- Started: `2026-07-13 13:28`

## Summary

- Landed the top must-do from plan 0010's follow-up roadmap: a neutron travel routine that coordinates a Spansh route without flying the ship. Operator flies each hop; routine sets the next waypoint in the galaxy map and watches the journal for arrival. Optional final station is handed off to the existing `transit_to_station` for docking so trade-route destinations flow end-to-end.
- Planning captured in `docs/plans/0012-neutron-travel-routine.md`; user design pushbacks (no in-game flight, composition-not-subclassing for `HaulRuntime`, station in v1 UI, unified `Route` now, server-side route cache with content-hash ids, cache as its own class) are recorded there under "Design pushbacks captured during planning".

## Changes

- New `edap/routines/spansh_route.py`: `fly_spansh_route(runtime, route, station, per_hop_timeout_s)` loops waypoints, setting each in gal-map, watching for arrival, announcing neutron heads-up on flagged waypoints, handing off to `transit_to_station` when a station is provided.
- Unified `Route` type in `edap/routing/types.py` replaces `InGameRoute` and `SpanshRoute`. Discriminated `InGameMetadata | SpanshMetadata | None` on `metadata`, tagged by `source` literal. `/api/route-compare` JSON payload reshaped accordingly; JS client updated.
- Extracted `RoutineRuntime`, `RoutineTiming`, `RoutineTravelSettings` (renamed from Haul*) into `edap/routines/runtime.py`. `HaulRuntime` and `HaulTiming` now compose them via a `routine:` field rather than subclass. `SupportsHaulControls` renamed to `SupportsRoutineControls`. `edap/control_room/routine_runtime_builder.py` holds `build_routine_runtime`; the haul builder composes it.
- `DESTINATION_SET` announcement moved into `set_galaxy_map_destination_for_transit` so every consumer gets the same pre-open heads-up; duplicate calls removed from undock/depart/travel. Phrase reworded to `"Opening galaxy map to set destination to {system_name}."`
- New `RouteCache` (`edap/routing/route_cache.py`): LRU-bounded, keyed by content hash of source/destination/range/efficiency/supercharge. Standalone class. `ControlRoomServerState` holds one and exposes `cache_spansh_route` / `get_spansh_route`. `/api/route-compare` returns `route_id` in the response.
- Dispatch chain: `command.dispatch_spansh_route` WS message → `ObserverSessionCommandHandler.dispatch_spansh_route(route, station, ...)` (server host resolves route_id → Route from server_state before calling) → backend/execution/facade → `routines_spansh.dispatch_spansh_route(app, ...)` → `fly_spansh_route(runtime, ...)`. Unknown/evicted route_id returns `invalid_command`.
- Web: `/haul` Route Comparison panel gains an optional Final station field; Switch to Spansh button becomes enabled once a Compare cached a route_id; click sends the dispatch through `window.EDCR_HAUL.sendCommand` (exposed from haul-ui.js so route-compare.js can share the socket).
- New TTS ids `SPANSH_NEUTRON_WAYPOINT_SET` and `SPANSH_ROUTE_COMPLETE` with default phrases.
- Tests: `test_route_cache.py`, `test_spansh_route.py`, WS handler tests for happy-path + unknown route_id in `test_control_room_server.py`, and `test_route_compare_endpoint.py` covers the cache round-trip. Full suite 777 tests, 0.402s.

## Follow-ups

- Live-validate the routine under CrossOver/macOS: hop transitions, jet-cone timing per neutron waypoint (operator-side), and final station handoff.
- Prefill Route Comparison from ship state (`supercharge_multiplier`, current system, `Loadout.MaxJumpRange`) — still open from plan 0010's must-do list.
- `RemoteObserverBackend.dispatch_spansh_route` currently emits a "not supported from remote python client" local message; wire it fully if/when a Python TUI wants this path.
