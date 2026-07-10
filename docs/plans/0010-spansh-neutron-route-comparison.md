# 0010: Spansh Neutron Route Comparison

## Status

In progress.

## Why

`travel <system>` currently sets a direct in-game galaxy-map route and follows it. For long-distance trips, the Spansh neutron plotter can produce a materially shorter route by chaining neutron-star boosts.

We want commanders to see, side-by-side, what the game's own plotter proposes versus what Spansh proposes for the same trip, so they can decide whether the neutron-boost overhead (extra galaxy-map visits, jet-cone maneuvering) is worth it. We also want a foundation that later supports auto-following the Spansh route waypoint-by-waypoint.

## Scope (v1)

Ship-free, offline-testable comparison surfaced on the web `/haul` page. This is deliberately narrow so we can iterate on the interesting bits (fetch, parse, diff, render) without needing the game running.

### In v1

- Fixtures captured from real Spansh + NavRoute.json responses.
- Pure parsers for NavRoute.json and the Spansh route response.
- Ship state extension: detect Mk II SCO FSD to auto-pick Spansh's Overcharge multiplier.
- Comparison layer producing side-by-side summaries, jump/neutron deltas, and a TTS phrase.
- New "Route Comparison (beta)" panel on `/haul`:
  - Inputs: from / to / range / efficiency / supercharge mode. Prefilled from ship state where possible.
  - Reads current `NavRoute.json` for the in-game side. Fetches Spansh for the other side.
  - Renders both routes side-by-side with per-hop LY and star class / neutron flags.
  - `?fixture=<name>` query param to render fixture pairs without hitting Spansh or reading the game — the offline dev/debug path.
- TTS announcement when a comparison completes.

### Not in v1 (parked)

- Neutron travel routine (per-waypoint hop loop that actually flies the Spansh route).
- "Switch to Spansh" button wired to routine dispatch (button exists, disabled).
- TUI comparison view.
- Laden jump-range calculation (use `Loadout.MaxJumpRange` and let commander edit).
- Replacing the existing travel panel.
- Any scoring beyond "Spansh saves/adds N jumps" (verdict rule: `spansh_better` iff jump count is lower).

## Architecture

Four layers, three of them pure so they are trivially testable offline.

```
edap/routing/navroute.py         parse NavRoute.json           (pure)
edap/spansh_router.py            call Spansh API + parse       (pure, httpx)
edap/routing/comparison.py       diff two typed routes         (pure)
edap/control_room/web + templates render side-by-side          (glue)
```

`edap/state.py` and the control-room state pipeline gain FSD-type + supercharge-multiplier fields so the web panel can auto-default correctly.

### Types

```python
@dataclass(frozen=True)
class RouteWaypoint:
    system: str
    star_class: str | None       # "N" for neutron; None on Spansh source rows
    neutron_boost: bool          # True on any neutron-flagged waypoint
    x: float; y: float; z: float
    ly_from_prev: float          # computed for NavRoute; from Spansh distance_jumped otherwise
    jumps_from_prev: int         # 1 for NavRoute; from Spansh `jumps` field otherwise

@dataclass(frozen=True)
class InGameRoute:
    waypoints: tuple[RouteWaypoint, ...]
    total_ly: float
    total_jumps: int
    neutron_count: int
    timestamp: str               # top-level NavRoute.json timestamp

@dataclass(frozen=True)
class SpanshRoute:
    waypoints: tuple[RouteWaypoint, ...]
    total_ly: float              # sum of distance_jumped
    total_jumps: int             # sum of `jumps`
    neutron_count: int           # count of waypoints with neutron_star=true
    galaxy_map_visits: int       # len(system_jumps) - 1
    source_system: str
    destination_system: str
    efficiency: int
    supercharge_multiplier: int

@dataclass(frozen=True)
class RouteComparison:
    in_game: InGameRoute
    spansh: SpanshRoute
    jumps_delta: int             # spansh.total_jumps - in_game.total_jumps  (negative = spansh saves)
    neutron_delta: int           # spansh.neutron_count - in_game.neutron_count
    verdict: Literal["spansh_better", "in_game_better", "even"]
    tts_phrase: str              # ready-to-speak, uses commander title
```

### TTS phrasing

Format: `"{title}, Spansh route came back and it {saves|adds} X jumps, with Y {more|fewer} neutron jumps, would you like to review?"`

`{title}` uses existing commander-title convention. `X` is `abs(jumps_delta)`; if `jumps_delta == 0` the phrase says "matches on jumps".

### Ship / FSD detection

Extend `Loadout` handling in `edap/state.py` to record:

- `ship["fsd_type"]`: `"overcharge_mkii" | "sco" | "standard" | None`, derived from `Modules[].Slot=="FrameShiftDrive"` Item string. Marker for Mk II SCO is `overchargebooster_mkii` in the Item name. `"sco"` matches `int_hyperdrive_overcharge_*`. Anything else is `"standard"`.
- `ship["supercharge_multiplier"]`: `6` if `fsd_type == "overcharge_mkii"` else `4`.

Mirror through `edap/control_room/models.ShipState`, `events.py`, `dependencies.py`, `protocol/data_messages.py`, `app.py`.

### Spansh call

`edap/spansh_router.py` uses `httpx` (already a dep) directly against `https://spansh.co.uk/api/route` and `/api/results/{job}`. No new dependency, no wrapper package. Poll interval and timeout configurable via function args; defaults tuned for the typical few-seconds turnaround. Returns `SpanshRoute`.

### Web panel

New panel on `/haul` titled "Route Comparison (beta)":

- Form fields: `from`, `to`, `range`, `efficiency` (default 60), `supercharge_mode` (`normal` / `overcharge`, default from ship's `fsd_type`).
- Prefill: `from` from ship's current system; `range` from `Loadout.MaxJumpRange` with a "unladen — reduce for cargo" hint.
- Buttons: **Compare**, **Refresh in-game route**, **Switch to Spansh** (disabled in v1, tooltip "coming soon").
- Result region: two-column table.
  - Header per side: total jumps · total LY · neutron count · (Spansh side also: galaxy-map visits).
  - Delta chip strip above the table: "Spansh saves 9 jumps · +5 neutron boosts".
  - Rows: system name, star class / neutron badge, `+LY` from previous, running total.
- `?fixture=<name>` query param bypasses live Spansh + NavRoute.json reads and renders from fixture files. Names: `hd232819_xinca_normal`, `hd232819_xinca_overcharge`.

## Fixtures

Under `tests/fixtures/routing/`:

- `navroute_hd232819_xinca.json` — copy of live NavRoute.json (HD 232819 → Xinca, 30 jumps, 1 neutron).
- `spansh_hd232819_xinca_normal_completed.json` — Spansh completed response, multiplier=4 (7 waypoints, 32 jumps).
- `spansh_hd232819_xinca_overcharge_completed.json` — Spansh completed response, multiplier=6 (6 waypoints, 22 jumps).
- `spansh_hd232819_xinca_queued.json` — Spansh in-progress response for polling tests.

## Execution

1. Commit fixtures on `main`.
2. Dispatch three Sonnet agents in parallel worktrees on file-disjoint slices:
   - `feat/navroute-parser`: `edap/routing/__init__.py` + `edap/routing/navroute.py` + `tests/test_navroute.py`.
   - `feat/spansh-router`: `edap/spansh_router.py` + `tests/test_spansh_router.py`.
   - `feat/fsd-overcharge-detection`: extend `edap/state.py` + `edap/control_room/models.py`, `events.py`, `dependencies.py`, `protocol/data_messages.py`, `app.py` + tests.
3. Verify each agent diff, cherry-pick onto `main`, remove worktrees.
4. Build `edap/routing/comparison.py` + tests.
5. Build the `/haul` panel + Starlette endpoint(s) + template + `?fixture=` support.
6. Full-suite test run.
7. Update `docs/status/travel.md`; create iteration log; refresh `docs/iteration-archive.md`.

## Acceptance

- Web panel on `/haul` renders side-by-side comparison from either live sources or `?fixture=`.
- Ship state exposes `fsd_type` and `supercharge_multiplier`; web panel auto-picks Overcharge on a Caspian with Mk II SCO.
- TTS phrase surfaces on comparison completion.
- All new modules covered by unit tests using fixtures; `uv run python3 -m unittest discover -s tests` passes.

## Non-Goals

- Actually flying a Spansh route.
- Any TUI work.
- Any change to existing `travel` routine behavior.
