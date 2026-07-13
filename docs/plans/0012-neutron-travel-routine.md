# 0012: Neutron Travel Routine

## Status

Not started. Planning only. Top must-do from plan 0010's Follow-up Roadmap.

## Why

`/haul`'s Route Comparison panel (plan 0010, v1 shipped) is advisory only. The "Switch to Spansh" button is disabled because no routine consumes the Spansh waypoint list. Until that lands, commanders who prefer the Spansh plot must set each waypoint in the galaxy map themselves. This plan fixes that gap.

## Scope of the routine

The routine coordinates, it does not fly. Per the repo-wide constraint, this project performs no in-game nav or flight actions. Concretely:

- At the current waypoint, we set the next Spansh waypoint in the galaxy map for the operator.
- Operator flies (jumps, and jet-cone-boosts if the waypoint is neutron-flagged) themselves.
- On arrival at that waypoint, if more remain, we set the next one. Repeat until the final waypoint.
- If the dispatch includes an optional station, hand off to `transit_to_station` after final-system arrival for docking.

Announcements exist to give the operator a heads-up at each hop. No supercruise actions, no landing, no combat. Everything the routine does is journal-watching plus galaxy-map interaction, both already supported by shared transit primitives.

## Prerequisite refactors

Three refactors land first so the new routine can compose cleanly. Each is small and tested independently.

### 1. Consolidate `InGameRoute` and `SpanshRoute` into a single `Route`

The two types already share `RouteWaypoint`. Only the metadata differs. A unified `Route` also unblocks a future "user-built route" source without a third type.

```python
@dataclass(frozen=True)
class InGameMetadata:
    timestamp: str

@dataclass(frozen=True)
class SpanshMetadata:
    efficiency: int
    supercharge_multiplier: int
    galaxy_map_visits: int

RouteMetadata = InGameMetadata | SpanshMetadata | None

@dataclass(frozen=True)
class Route:
    waypoints: tuple[RouteWaypoint, ...]
    total_ly: float
    total_jumps: int
    neutron_count: int
    source: Literal["in_game", "spansh", "user"]
    source_system: str
    destination_system: str
    metadata: RouteMetadata
```

Python has no Swift-style associated-enum. Discriminated union via the `source` tag with `match`/isinstance on `metadata` is the closest idiomatic shape.

Touches: `edap/routing/types.py`, `edap/routing/navroute.py`, `edap/spansh_router.py`, `edap/routing/comparison.py`, `edap/routing/web.py`, tests, and the `/api/route-compare` JSON shape (client field names for `spansh` extras move under a `metadata` object). `web/route-compare.js` updates accordingly.

### 2. Extract `RoutineRuntime` from `HaulRuntime` via composition (not inheritance)

`HaulRuntime` currently carries generic transit dependencies plus haul-specific `market_path` and `market`. `edap/routines/travel.py` already reuses `HaulRuntime` outside a hauling context, which is the smell.

Shape:

```python
@dataclass
class RoutineRuntime:
    controls: SupportsRoutineControls   # renamed from SupportsHaulControls
    watcher: SupportsPollEvents
    journal_dir: Path
    timing: RoutineTiming               # renamed shared subset of HaulTiming
    travel: RoutineTravelSettings       # renamed from HaulTravelSettings
    time_fn: Callable[[], float]
    sleeper: Callable[[float], None]
    progress_fn: ProgressCallback
    announce_fn: AnnouncementCallback

@dataclass
class HaulRuntime:
    routine: RoutineRuntime             # composition, not subclass
    market_path: Path
    market: HaulMarketSettings

@dataclass
class HaulTiming:
    routine: RoutineTiming              # composition
    max_hold_s: float
    trade_timeout_s: float
    post_sell_settle_s: float
```

Haul call sites that read `runtime.controls` become `runtime.routine.controls`; where a haul routine hands off to transit, it passes `runtime.routine` down. Bigger diff than subclassing, chosen for clean separation. Existing structural `TransitRuntime` Protocol in `transit.py` continues to be satisfied by `RoutineRuntime`.

### 3. Move the runtime builder out of `routines_haul.py`

`_build_haul_runtime` currently lives in `edap/control_room/routines_haul.py`. The generic half is extracted to a new module `edap/control_room/routine_runtime_builder.py` exposing `build_routine_runtime(app, ...)`. `_build_haul_runtime` stays in `routines_haul.py` but now composes: `HaulRuntime(routine=build_routine_runtime(app, ...), market_path=..., market=...)`.

## Gal-map pre-announcement

Existing `AnnouncementId.DESTINATION_SET` fires from `undock_and_route_to_system` and `depart_system_to_route` before `set_galaxy_map_destination_for_transit` runs. Current phrase: `"Setting destination to {system_name}."` The primitive itself does not announce.

**Change:** move the `DESTINATION_SET` announcement inside `set_galaxy_map_destination_for_transit` so every consumer (undock, depart, spansh-route) gets it, and delete the now-duplicate calls at the two existing call sites. Rephrase to `"Opening galaxy map to set destination to {system_name}."` so the intent is explicit.

Not adding a new `OPENING_GALAXY_MAP` id — the reworded `DESTINATION_SET` covers it.

## Server-side route cache

`/api/route-compare` already computes the Spansh route server-side; only the client currently holds it. To avoid re-fetching on "Switch to Spansh" and to keep the dispatch payload small, cache Spansh routes on the server.

New module `edap/routing/route_cache.py`:

```python
@dataclass(frozen=True)
class RouteRequestKey:
    source_system: str
    destination_system: str
    range_ly: float
    efficiency: int
    supercharge_multiplier: int

class RouteCache:
    def __init__(self, *, max_entries: int = 16) -> None: ...
    def put(self, route: Route, *, request_key: RouteRequestKey) -> str: ...   # returns id
    def get(self, route_id: str) -> Route | None: ...
    def __len__(self) -> int: ...
```

- Standalone class so tests exercise it without any server fixture.
- Id is a short stable hash of `RouteRequestKey`. Same key returns the same id; any input change produces a new id and triggers a new Spansh fetch upstream.
- LRU eviction at `max_entries`.

`ServerState` holds one `RouteCache` and exposes thin `cache_spansh_route` / `get_spansh_route` wrappers. `/api/route-compare` populates it and returns `route_id` in the JSON response. Client stores that id alongside the last successful compare.

## Neutron travel routine

New module `edap/routines/spansh_route.py` with:

```python
def fly_spansh_route(
    runtime: RoutineRuntime,
    *,
    route: Route,
    station: str = "",
) -> RoutineResult: ...
```

Loop (skipping `waypoints[0]`, the source system):

1. Determine `next_wp`.
2. `set_galaxy_map_destination_for_transit(runtime, next_wp.system, routine_name="spansh_route")` (which now handles the "opening galaxy map" announcement itself).
3. If `next_wp.neutron_boost`, announce a neutron heads-up (`SPANSH_NEUTRON_WAYPOINT_SET`).
4. `wait_for_arrival_or_approach_event(...)` until arrival in `next_wp.system`, with a per-hop timeout.
5. If more waypoints remain, loop. Otherwise:
   - No station: announce `SPANSH_ROUTE_COMPLETE`, return `ok`.
   - With station: `transit_to_station(runtime, destination=TravelDestination(system=final_system, station=station), assume_arrived_in_destination_system=True, ...)`.

Timeout at any leg returns an `error` `RoutineResult` naming the failed waypoint.

New announcement ids and default phrases:

- `SPANSH_NEUTRON_WAYPOINT_SET`: `"Neutron boost ahead: {system_name}."`
- `SPANSH_ROUTE_COMPLETE`: `"Spansh route complete, arrived at {system_name}."`

## Dispatch plumbing

Mirror the existing `dispatch_travel` chain:

- New WS command `command.dispatch_spansh_route` in `edap/control_room/server/app.py`. Payload: `{ route_id: str, station?: str }`. On unknown or evicted id, return `invalid_command` with a clear "route no longer cached, run Compare again" message.
- `CommandHandler` protocol + server host (`edap/control_room/server/host.py`, `commands.py`) + facade + backend (`edap/control_room/backend.py`) + client backend (`edap/control_room/client/backend.py`) gain `dispatch_spansh_route(...)`.
- New module `edap/control_room/routines_spansh.py` with `dispatch_spansh_route(app, *, route, station, ...)` mirroring `routines_travel.dispatch_travel`. Uses `build_routine_runtime(app, ...)` and calls `fly_spansh_route(runtime, route=route, station=station)` inside `_start_delayed_routine`.

## Web UI

- Enable `#rc-switch` in `web/haul-v1.html`: remove `disabled`, drop the `title="coming soon"`.
- Add a station field on the Route Comparison panel (part of v1). Prefills from the currently-selected trade route if one is active; otherwise empty. Cleared field means system-only travel.
- `web/route-compare.js`: store `route_id` from the last successful Compare response. On `#rc-switch` click, send `command.dispatch_spansh_route` with `{ route_id, station: <field value or "" > }` over the WS.

## Tests

- `RouteCache` unit tests: put/get roundtrip, id stability for equal keys, LRU eviction, `get` on unknown id returns None.
- Unified `Route` type: parser tests updated (`test_navroute.py`, `test_spansh_router.py`), `test_route_comparison.py` updated for new `metadata` shape.
- `fly_spansh_route` tests using fake runtime doubles: happy-path multi-hop loop, single-hop, neutron heads-up, timeout at hop N, station handoff at end.
- `dispatch_spansh_route` WS handler tests: unknown route_id → invalid_command; happy path → dispatch invoked with expected route + station; missing station falls back to `""`.
- `test_routing_web.py` updated for the new payload shape (metadata under `metadata`, plus `route_id`).
- Full-suite budget: `758+ tests * 0.0006s` must hold. Any regression triggers `tools/report_test_timing.py`.

## Execution order

1. Consolidate `Route` type + update `navroute`, `spansh_router`, `comparison`, `web`, JS field names, tests.
2. Extract `RoutineRuntime` (composition) + rename `SupportsHaulControls`, `HaulTiming`, `HaulTravelSettings`. Rewire `travel.py`, `HaulRuntime`, haul routines. Move builder to `routine_runtime_builder.py`.
3. Move `DESTINATION_SET` into `set_galaxy_map_destination_for_transit`; delete duplicate call sites; update phrase.
4. `RouteCache` module + tests. Wire into `ServerState`. `/api/route-compare` returns `route_id`. Client stores it.
5. `edap/routines/spansh_route.py` + new announcement ids/phrases + tests.
6. `edap/control_room/routines_spansh.py` + `dispatch_spansh_route` through backend/facade/host/commands + WS handler in `app.py` + tests.
7. Enable `#rc-switch` + add station field on Route Comparison panel + JS wiring.
8. Iteration log; update `docs/status/travel.md` and flip plan 0010's follow-up roadmap top item to "shipped".

## Design pushbacks captured during planning

These were course-corrections during the design conversation. Recorded here so the intent is preserved.

- **No in-game flight actions.** Initial sketch had the routine "perform jet-cone supercharge maneuver" on neutron waypoints. Rejected: this project does not fly the ship. Routine coordinates only; operator handles all flight (including jet-cone boosts). Neutron waypoints get an announcement, not an action.
- **Per-waypoint galaxy-map setting is our job.** We set waypoint N+1 in the galaxy map at waypoint N. The loop is set → wait for arrival → set next, not "set final destination and let the game route between neutron boosts."
- **`HaulRuntime` should not be reused outside haul.** Original proposal used `HaulRuntime` directly for the new routine (`travel.py` already does this). Rejected: extract a `RoutineRuntime` and have `HaulRuntime` depend on it via composition, not subclassing. Same treatment for `HaulTiming`.
- **Builder does not stay in `routines_haul.py`.** Original proposal kept `_build_routine_runtime` alongside `_build_haul_runtime` in the haul module. Rejected: the routine-runtime builder gets its own module (`edap/control_room/routine_runtime_builder.py`).
- **No duplicate gal-map announcements.** Original proposal added a new `OPENING_GALAXY_MAP` id. Rejected: the existing `DESTINATION_SET` announcement (currently fired from each caller before `set_galaxy_map_destination_for_transit`) already serves this beat. Move it inside the primitive, delete duplicates, and reword to `"Opening galaxy map to set destination to {system_name}."`
- **Optional station belongs in v1, including the web UI.** Original proposal exposed the parameter through the dispatch but deferred the panel field to a follow-up. Rejected: station field is part of v1 on `/haul`, so a trade-route selection can flow end-to-end.
- **Consolidate `InGameRoute` and `SpanshRoute` now.** Original proposal kept them separate as low-risk. Rejected: they overlap almost entirely and a future user-built route source is foreseeable. Do the consolidation now while it is cheap.
- **Server holds the Spansh route, not the client.** Original proposal serialized waypoints into the dispatch payload. Corrected: server already computes the comparison, so it should cache the route and hand the client a short `route_id` to reference. Cache supports multiple concurrent routes so flipping between destinations does not re-fetch. Id is a content hash so any changed input triggers a new Spansh fetch upstream.
- **Route cache is its own class.** Not folded into `ServerState`; standalone `RouteCache` in `edap/routing/route_cache.py` so it can be tested without any server fixture. `ServerState` just holds one.

## Non-goals

- Any in-game flight or supercruise action.
- Jet-cone boost automation.
- Docking automation beyond what `transit_to_station` already provides.
- Consolidating the Route Comparison and Travel Assist panels (parked idea from plan 0010).
