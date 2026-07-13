# Travel Status
## Current
- Neutron travel routine `fly_spansh_route` ships: `/haul` "Switch to Spansh" now dispatches `command.dispatch_spansh_route { route_id, station? }`; server resolves `route_id` via `RouteCache` on `ControlRoomServerState`, per-waypoint we set the next system in the galaxy map and wait for arrival, optional final station hands off to `transit_to_station`. Operator flies each hop; routine never touches nav/flight.
- Runtime refactor: `RoutineRuntime` (composed, not subclassed) is what travel and spansh routines take; `HaulRuntime`/`HaulTiming` compose it. Builder lives in `edap/control_room/routine_runtime_builder.py`, out of the haul module.
- `DESTINATION_SET` announcement fires from inside `set_galaxy_map_destination_for_transit` (single source), reworded to `"Opening galaxy map to set destination to {system_name}."` — all callers get the same pre-open heads-up.
- `InGameRoute`/`SpanshRoute` consolidated into one `Route` with discriminated `metadata`; the `/api/route-compare` JSON nests source-specific fields under `metadata` and returns a `route_id`.
- `/haul` "Route Comparison (beta)" panel is a full-width section above the layout grid; the endpoint publishes an `AnnouncementEvent(spansh_route_ready)` through the broker so all connected observers speak the phrase via the existing TTS pipeline. Panel now has an optional Final station field for trade-route hand-off.
- Route Comparison panel backed by `/api/route-compare` renders in-game `NavRoute.json` and Spansh neutron plot side-by-side. `?fixture=hd232819_xinca_{normal,overcharge}` bypasses live sources for offline dev.
- Ship state exposes `fsd_type` (`standard`/`sco`/`overcharge_mkii`) and `supercharge_multiplier` (4 or 6) from Loadout, detected by FSD module Item marker `overchargebooster_mkii`.
- `travel <system> [/ <station>]` starts server-first assistive travel; station optional. Supports docked, normal-space, and supercruise start states, plus other-system targets via galaxy-map route.
- TUI haul search results support `t` to save the highlighted route and start `travel`; the `/haul` web Travel Assist fields autofill from the selected route.
- Shared station transit, route retry/unconfirmed-route handling, manual surface handoff, and interdiction abort behavior live in `edap.routines.transit` for travel, two-way haul, multi-leg haul, and now spansh route.
## Caveats
- Live validation still needed for all start states under CrossOver/macOS, especially docked launch into same-system station travel and multi-jump resume. Neutron routine end-to-end has not been exercised against a live journal yet.
- Surface/on-land travel inherits manual landing handoff; settlement approach automation is not implemented.
## Next
- Live-validate `fly_spansh_route` under CrossOver/macOS: hop transitions, jet-cone timing per neutron waypoint (operator-side), and final-station handoff via `transit_to_station`.
- Prefill Route Comparison panel from ship state (`supercharge_multiplier`, current system, `Loadout.MaxJumpRange`) — the other remaining must-do from plan 0010's follow-up roadmap.
- Live-validate `travel` from docked, same-system supercruise, normal-space, and remote-system starts before expanding the web UI or adding route-search handoff affordances.
