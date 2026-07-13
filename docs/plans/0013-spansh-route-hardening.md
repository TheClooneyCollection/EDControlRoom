# 0013: Spansh Route Hardening

## Status

Not started. Planning only. Follow-up to plans [0010](0010-spansh-neutron-route-comparison.md) (Route Comparison) and [0012](0012-neutron-travel-routine.md) (Neutron travel routine).

## Why

Plan 0012 shipped `fly_spansh_route` and the four-button web panel from the follow-up session. Live operator feedback surfaced four concrete gaps that keep the routine from feeling like `travel` for Spansh plots:

1. The All-in-one retry / wait-for-NavRoute loop lives in the browser, so a TUI or Python client would re-implement it. Retry policy belongs in one place: the server.
2. `fly_spansh_route` only sets the next waypoint in the galaxy map. It does not undock or boost away when the operator starts docked or in normal space. `travel` already handles this via `undock_and_route_to_system` / `depart_system_to_route`; the Spansh routine skips those primitives.
3. The `destination_set` TTS phrase ("Opening galaxy map to set destination to X.") is firing mid-route between waypoints. Root cause is in `edap/control_room/app.py:1498`: the `FSDTarget` journal event fires the same `AnnouncementId.DESTINATION_SET`, and `FSDTarget` fires on every hyperspace target lock, not only when the operator actually opens the galaxy map. Two distinct events share one id.
4. No panel shows Spansh route progress. The active haul routine card is the mental model; a similar Active route card would let the operator see where they are without leaving the browser.

## Scope

Four independent slices. Each is small enough to ship and validate on its own. Ordered by highest-friction first.

### 1. Split `DESTINATION_SET` into two announcement ids

**Problem.** `AnnouncementId.DESTINATION_SET` is emitted from two places:

- `edap/routines/transit.py:269` inside `set_galaxy_map_destination_for_transit`. Semantics: the routine is about to open the galaxy map and pick a system. Phrase makes sense.
- `edap/control_room/app.py:1498` in `_announce_tts_for_event` on `FSDTarget`. Semantics: the FSD locked onto a target star. This fires between waypoints, not only when destination is being set. Phrase does not fit.

**Fix.** Introduce a new id and rename the existing one so each site tells a distinct story:

- Keep `DESTINATION_SET` for the routine site. Phrase stays: "Opening galaxy map to set destination to {system_name}."
- Add `FSD_TARGET_LOCKED` (or similar; naming to confirm) for the journal-event site. Phrase: something like "Target locked: {system_name}." Short, does not imply operator action.

Update `defaults/tts.toml`, `edap/tts.py`, and `edap/control_room/app.py:1498`. Both phrases should be individually mutable in the `[tts.phrases]` config and silenceable via `tts.disabled_messages`.

**Tests.** Verify each site emits its own id; `test_control_room.py` FSDTarget path currently asserts the shared id.

### 2. Undock / boost-away handoff in `fly_spansh_route`

**Problem.** `fly_spansh_route` today just loops `set_galaxy_map_destination_for_transit` starting from `waypoints[1]`. If the operator dispatched the routine while docked or in normal space, nothing kicks them into supercruise.

**Fix.** Before the per-waypoint loop, do the same phase detect that `travel_to_station` does:

- Read `read_ship_position(runtime.journal_dir)`.
- If `status == "docked"`, call `undock_and_route_to_system(...)` targeting `waypoints[1].system` and treat its result as the first hop. Skip the manual `set_galaxy_map_destination_for_transit` for waypoint 1 in that case (the undock primitive already sets the route).
- If `status == "normal_space"`, call `depart_system_to_route(...)` for the same first hop and skip the manual set.
- If `status == "supercruise"`, current behavior is fine but confirm the game accepts the route.

Then continue the existing loop from `waypoints[2]` onward. On arrival at the final system, keep the optional `transit_to_station` handoff.

**Constraint.** Repo rule: no in-game flight actions we did not already do in transit. Undock, depart, and station-transit primitives are all pre-approved. No new low-level nav from this plan.

**Tests.** Extend `tests/test_spansh_route.py` with a docked-start and a normal-space-start fixture; assert we called the right primitive and that waypoint 1 is not double-set.

### 2b. Drop the per-hop arrival timeout

**Problem.** `fly_spansh_route` today times out each Spansh-leg wait at `runtime.timing.dock_timeout_s` (default `1200s`, config key `controls.haul.dock_timeout_seconds` in `defaults/controls.toml:20`). That key was picked because `HaulTiming.dock_timeout_s` forwards from `RoutineTiming.dock_timeout_s`, but its meaning here is unrelated to docking — it caps the wall time between "we set waypoint N" and "ship enters waypoint N's system," which spans every in-between plain-system FSD jump plus any operator break, bio-scan detour, or jet-cone re-align.

The routine does not fly the ship, and the operator can already pause / stop / resume via the existing routine controls. A hard timeout only converts "operator went to make coffee" into "routine aborted, dispatch from scratch."

**Fix.** Remove the timeout. In `edap/routines/spansh_route.py`, drop the `per_hop_timeout_s` parameter on `fly_spansh_route`, drop the `hop_timeout` local, and pass `math.inf` as the `deadline` to `wait_for_arrival_or_approach_event`. `wait_for_arrival_or_approach_event`'s signature stays as-is; only the Spansh caller opts into "no deadline." Haul and travel callers keep their real timeouts because they do fly (undock, dock) and a runaway wait there indicates a stuck operation, not an operator break.

`JournalWatcher.poll()` already paces internally via `self._sleep()`, so an infinite wait loop does not burn CPU.

**Tests.** Update `tests/test_spansh_route.py`: remove the timeout-abort case, add a case that verifies the loop yields as soon as an arrival event arrives regardless of elapsed time in `time_fn`.

### 3. Move All-in-one retry to the server

**Problem.** Today the browser sequences: `command.dispatch_destination` -> `GET /api/spansh-route` -> `sleep(wait)` -> `GET /api/route-compare` (retry on 404). Any non-browser client (TUI, Python REPL) would have to reimplement this.

**Fix.** Introduce a server-orchestrated "all in one" command. Two options; recommend option A.

**Option A. New composite command `command.dispatch_route_all_in_one`.**

Payload: `{ from, to, range, efficiency, supercharge_multiplier, station? }` plus optional overrides for `navroute_wait_seconds` and `compare_retry_attempts` (defaults come from `ControlRoomConfig`). The server handler:

1. Dispatches `dispatch_destination` under the hood (or invokes the same code path).
2. Fetches Spansh, caches the route.
3. Loops: sleep `navroute_wait_seconds`; attempt to read `NavRoute.json`; if unreadable / stale, retry up to `compare_retry_attempts`. Once NavRoute is fresh, run the compare and cache.
4. Publishes progress via existing `AnnouncementEvent` / activity-log fanout so any observer (web, TUI) sees the same trail.
5. Returns the final `route_id` + comparison payload in the command response.

Response shape mirrors `/api/route-compare` today plus a `phases` array describing what happened at each step, so clients can render a checklist.

**Option B. Server-side helper endpoint `POST /api/route-compare/all-in-one`.**

Same behavior, but expressed as HTTP instead of a WS command. Simpler wire, but less consistent with the rest of the routine surface. Prefer A.

**Client.** Web `allInOne()` becomes a single `sendCommand("command.dispatch_route_all_in_one", ...)` call and renders the phased response. The two config inputs stay on the panel as per-session overrides in the command payload.

**Config.** Existing `control_room.route_compare_navroute_wait_seconds` and `route_compare_compare_retry_attempts` remain the source of truth; the client just presents them and lets the operator edit.

**Tests.** Command-handler unit test with a fake NavRoute that returns 404 twice then succeeds; verify retry count, sleep count, and final response. WS backend passthrough test. Web JS becomes thinner.

### 4. Active route panel

**Problem.** During a Spansh run the operator has no in-panel view of where they are. Route Comparison shows the plan; nothing shows progress.

**Fix.** New card on `/haul` styled like the Active haul routine card:

```
Active route  ·  Spansh, 22 jumps, 6 boosts
Last waypoint  →  X systems  →  Current: <system>  →  Y more systems  →  Next: <system>
```

Data sources already available:

- Current system: `ShipState.system` from hydrate + `ship.updated` events.
- Cached Spansh route: `broker.server_state.get_spansh_route(route_id)`.
- Local NavRoute for the fallback "in-game" case: same read path Compare uses.

Backend: broker persists the currently-active `route_id` (already partially there via `RouteCache`) plus a small `active_route` record when `dispatch_spansh_route` starts. Hydrate/event stream include this record.

UI: new card between the routine bar and the Route Comparison panel. Uses hydrate + `ship.updated` to recompute the "X systems behind / Y systems ahead" split by finding `ShipState.system` in the cached route's waypoints.

**Tests.** Broker persistence + hydrate payload shape. JS unit isn't practical here without a headless-DOM harness; skip.

## Non-goals

- No changes to jet-cone / boost mechanics (still operator-driven per project scope).
- No auto-plot on new `NavRoute.json` (still parked from plan 0010).
- No TUI mirror of the Active route panel; wire it after the web version proves out.

## Execution order

1. Slice 1 (TTS id split). Smallest and unblocks operator feedback about the mid-route announcement noise.
2. Slice 2 (undock/boost handoff). Makes the routine usable from any start state.
3. Slice 2b (drop the arrival timeout). Trivially small; ship alongside slice 2 or immediately after.
4. Slice 3 (server-side retry). Removes client duplication and prepares the ground for slice 4.
5. Slice 4 (Active route panel). Needs slice 3's server-side lifecycle to know when a route becomes active.

## Design pushbacks captured during planning

- User called out that retries belong on the server, not the browser. Slice 3 is a direct response; the shipped client-side retry is a stopgap.
- User called out that the Spansh routine only sets destination and does not undock / boost like `travel`. Slice 2 is a direct response.
- User called out the mid-route "opening galaxy map" TTS. Root cause traced to two announcement sites sharing `AnnouncementId.DESTINATION_SET`. Slice 1 splits them rather than silencing either.
- Active route panel wording follows the operator's mental model: "last waypoint -> X systems -> Current -> Y systems -> Next waypoint." Keep that phrasing in the UI copy.
- User asked why the Spansh routine has a per-hop timeout at all. Since the routine does not fly the ship and pause / stop / resume already exist, a hard timeout only punishes operator breaks. Slice 2b removes it rather than adding a dedicated `spansh_waypoint_arrival_timeout_seconds` config key. Haul and travel keep their real timeouts because those routines drive actual undock / dock actions where a stuck wait is a genuine error signal, not just an idle operator.
