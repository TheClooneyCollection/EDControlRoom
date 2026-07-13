# Iteration Log

- Area: `travel`
- Title: `spansh-hardening-slice-2-undock-and-no-timeout`
- Started: `2026-07-13 15:56`

## Summary

- Plan 0013 slices 2 + 2b. `fly_spansh_route` now handles docked and normal-space starts via the shared `undock_and_route_to_system` / `depart_system_to_route` primitives (same handoff `travel` uses), so operators can dispatch it from any state. Per-hop arrival deadline is gone: the operator drives every hop and the existing routine pause/stop/resume is the cancellation surface. `wait_for_arrival_or_approach_event` signature is unchanged; only the Spansh caller opts into `math.inf`.

## Changes

- `edap/routines/spansh_route.py`: read `read_ship_position(runtime.journal_dir)` at entry. When `docked`, call `undock_and_route_to_system(destination_system=waypoints[1].system)`. When `normal_space`, call `depart_system_to_route(...)`. Both branches skip the manual galaxy-map-set for waypoint 1 (primitive already sets the route). Announce `SPANSH_NEUTRON_WAYPOINT_SET` if waypoint 1 is a neutron. Loop continues from `waypoints[2:]`. Supercruise / unknown falls back to the existing per-waypoint galaxy-map pattern from `waypoints[1:]`. Dropped `per_hop_timeout_s` parameter and pass `math.inf` as the deadline. Removed the "timed out" error branch (unreachable with no deadline, and the operator already has pause/stop/resume).
- `tests/test_spansh_route.py`: replaced the timeout test with `test_arrival_short_circuits_regardless_of_elapsed_time` (uses a `time_fn` that jumps forward an hour per tick to prove there is no per-hop deadline). Added `test_docked_start_uses_undock_primitive_for_first_hop` (asserts `undock_and_route_to_system` is called for waypoint 1 and the galaxy-map set is NOT re-run for waypoint 1), `test_normal_space_start_uses_depart_primitive_for_first_hop`, and `test_docked_start_propagates_undock_failure`.

## Follow-ups

- Slice 3: move All-in-one retry to server (`command.dispatch_route_all_in_one`).
- Slice 4: Active route panel on `/haul`.
- Live-validate docked/normal-space Spansh start under CrossOver/macOS.
