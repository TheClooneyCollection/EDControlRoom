# 0022: Cheapest Markets for a Commodity

## Status

Decisions confirmed 2026-11-27; nothing built. Mission M7.

## Why

Buying one commodity (Tritium for a carrier, say) means finding the cheapest market that has enough of it and fits the ship, near where you are. Today that takes Inara or Spansh in a browser. The hub already holds a week of EDDN prices, and Spansh's station search covers the rest.

## Findings (2026-11-27, reference Adach)

- Spansh `POST https://spansh.co.uk/api/stations/search`, no auth. Price sort works with `"sort":[{"market_buy_price":[{"name":"Tritium","direction":"asc"}]}]` (`market_sell_price` sorts by the price the station pays, so it looked broken). Server-side filters that work: `market[].supply` range, `distance` `{"min","max"}` (ly from `reference_system`), `market_updated_at` date range (`"comparison":"<=>"`), `has_large_pad`, and `type` as an allow-list of values. `type` with `"invert":true` is ignored, so carriers are excluded by listing station types, not by negation. `count` caps at 10000.
- Result rows carry `market_id`, `name`, `type`, `system_name`, `system_x/y/z`, `distance`, `distance_to_arrival`, `has_large_pad` (no medium flag), `market_updated_at`, and `market[]` with `commodity`, `buy_price`, `supply`.
- The hub store (`price` + `market` + `station` + `system`) had 5536 stations and 236 carriers selling Tritium, all updated in the last 7 days, and 428k system coordinates. Its cheapest station within 200 ly of Adach with supply at least 1000 (Rippert Legacy, 44,862 cr) matched Spansh's.
- Carrier prices are often fake: 2565 cr (54 carriers) and 5,129,400 cr (11 carriers). Spansh shows the same, plus carriers last updated in 2020. Many stations list tiny supply (20 units).
- Inara: blocks headless browsers (fingerprinting). Not a source.

## Decisions (confirmed with the user)

- Hub first, Spansh fills in. The hub answers from its own store; one Spansh search per query adds older or farther markets. Rows merge by `market_id`, newer `updated_at` wins, and each row is marked `hub` or `spansh`. A Spansh failure leaves the hub rows and shows the error; it never blocks the page.
- Carriers are excluded by default, with the count shown ("12 carriers hidden"). A toggle shows them, each marked as a carrier; a carrier price under 10% of the median station price for the commodity is flagged "price looks fake".
- Defaults follow the viewed node's ship: pad = the ship's required pad size, min supply = its cargo capacity, reference system = its current system, max age 7 days, radius 100 ly. All are editable; radius can be cleared for galaxy-wide.
- A new page `/cheapest` (`/markets` is already the recent-markets page), linked in the nav.
- Nothing filtered disappears silently: the payload carries counts per reason (`carrier`, `pad`, `supply`, `age`, `radius`) for the hub rows, and Spansh's server-side filtering is described in the footer ("Spansh: filtered server-side, 3366 matches").
- No bulk dumps. Spansh is one search request per query (`size` 50).

## Rejected

- Spansh only: ignores data the hub already has and makes every query depend on the network.
- Hub only: coverage is limited to the listener's week plus the VPS snapshot.
- Paging Spansh by distance and sorting locally: reaches about 60 ly per 500 rows; the price sort makes it unnecessary.
- Inara scraping: blocked.
- A section inside `/routes`: that page is already crowded and its controls are route-shaped.

## Design

### Fixed interfaces

`edcr/cheapest_markets.py` (slice A owns it):

```python
PAD_ORDER = {"S": 1, "M": 2, "L": 3}

@dataclass(frozen=True)
class CheapestQuery:
    commodity: str              # EDDN symbol, lower case: "tritium"
    reference_system: str       # "" = no distance column and no radius
    radius_ly: float | None     # None = galaxy-wide
    min_supply: int
    pad: str                    # "S" | "M" | "L": the smallest pad the ship can use
    max_age_hours: float
    include_carriers: bool
    use_spansh: bool
    limit: int                  # 50

@dataclass(frozen=True)
class MarketOffer:
    source: str                 # "hub" | "spansh"
    market_id: int
    system_name: str
    station_name: str
    station_type: str           # "" when unknown
    is_carrier: bool
    max_pad: str                # "S" | "M" | "L" | "" unknown
    dist_ls: float | None
    distance_ly: float | None   # None when no reference system
    buy_price: int
    supply: int
    updated_at: float           # epoch seconds
    suspect_price: bool         # carrier price under 10% of the station median

@dataclass(frozen=True)
class CheapestResult:
    offers: list[MarketOffer]   # sorted by buy_price, then distance_ly
    hidden: dict[str, int]      # reason -> count, hub rows only
    spansh_count: int | None    # Spansh's total matches; None when not asked
    spansh_error: str           # "" when fine

def parse_cheapest_query(params: Mapping[str, str], *, current_system: str,
                         cargo_capacity: int, ship_pad: str) -> CheapestQuery  # ValueError on bad input
def query_hub_store(db: Path, query: CheapestQuery, *, now: float) -> tuple[list[MarketOffer], dict[str, int]]
def merge_offers(hub: list[MarketOffer], spansh: list[MarketOffer], query: CheapestQuery) -> list[MarketOffer]
def cheapest_payload(result: CheapestResult, query: CheapestQuery, display_name: str) -> dict[str, Any]
```

`edcr/spansh_stations.py` (slice B owns it):

```python
# Post a JSON body to a URL within a timeout in seconds; returns decoded JSON, raises on failure.
PostJson = Callable[[str, dict[str, Any], float], object]

def spansh_search_body(query: CheapestQuery, commodity_name: str) -> dict[str, Any]
def search_cheapest(query: CheapestQuery, commodity_name: str, post: PostJson,
                    *, now: float) -> tuple[list[MarketOffer], int]  # (offers, Spansh count)
```

`commodity_name` is the display name Spansh expects ("Tritium"); the hub has it from recent markets' display names, falling back to title-casing the symbol. Spansh pad: `L` when `has_large_pad`, else `""`. Carrier: `type` contains `Carrier`. The station-type allow-list lives in this module.

`edcr/ship_types.py` (slice C) gains `SHIP_PAD_SIZES: dict[str, str]` (journal ship type -> `S`/`M`/`L`) and `ship_pad_size(ship_type: str) -> str` (`""` when unknown; the caller then uses `haul_search.toml` `min_landing_pad`).

HTTP: `GET /api/cheapest-markets?commodity=tritium&system=Adach&radius_ly=100&min_supply=720&pad=L&max_age_hours=168&carriers=0&spansh=1&node=<id>`. Missing params take the ship defaults above. Payload:

```json
{"commodity": "tritium", "name": "Tritium", "query": {...resolved CheapestQuery...},
 "offers": [{...MarketOffer..., "age_s": 3600}],
 "hidden": {"carrier": 236, "supply": 4100, "pad": 12, "age": 0, "radius": 5200},
 "spansh": {"asked": true, "count": 3366, "error": ""}}
```

Hub protocol: `REQUEST_CHEAPEST_MARKETS = "cheapest_markets"` in `edcr/hub/protocol.py`. A peer forwards its resolved params to the hub, like `REQUEST_EDDN_ROUTES`. The hub runs both the store query and the Spansh call; peers never call Spansh.

### Matching rules (hub store)

- Rows: `price.commodity = ?`, `supply > 0`, joined to `market`, `station` (pad, type, dist_ls) and `system` (coordinates).
- Pad: keep when `PAD_ORDER[max_pad] >= PAD_ORDER[query.pad]`; unknown pad is kept and shown as `?`.
- Age: `market.updated_at >= now - max_age_hours * 3600`.
- Radius: needs the reference system's coordinates from `system`; a reference the store does not know returns 404 "Unknown system" unless `use_spansh`, in which case Spansh's `distance` is used and hub rows show no distance.
- Each failed rule adds to `hidden[reason]` (first failing rule only, in the order carrier, pad, supply, age, radius).
- Spansh rows for a `market_id` the hub also has are dropped in favour of the newer row; when the Spansh row wins, the hub's `station.max_pad` fills the missing medium pad.

### Slices (by file ownership)

- A: `edcr/cheapest_markets.py`, `tests/test_cheapest_markets.py`. Query parsing, store query, merge, suspect-price flag, payload. Tests use a temp SQLite built with `EddnStore`.
- B: `edcr/spansh_stations.py`, `tests/test_spansh_stations.py`. Body builder and response parsing with an injected `PostJson`; no network in tests. The production `PostJson` uses `httpx` with a 10 s timeout. Depends only on A's dataclasses (stub them from this plan if A is not merged yet).
- C: `edcr/ship_types.py` pad table, `edcr/hub/protocol.py` request kind, `edcr/control_room/server/app.py` endpoint and hub/peer routing (mirror `eddn_routes`: `node=` reads the peer's ship from hub state), tests in `tests/test_control_room_cheapest.py`. Depends on A and B.
- D: `web/cheapest.html`, `web/cheapest.js`, `web/nav.js` entry, static route in app.py's asset table (coordinate with C: D adds only the page route and the `cheapest.js` MIME entry). Form (commodity, system, radius, min supply, pad, max age, carriers toggle, Spansh toggle), results table (price, supply, station, system, distance ly, arrival Ls, pad, age, source), hidden counts line, Spansh status line. Rows older than 24 h show age in amber; carrier rows carry a badge; suspect prices are struck through with a tooltip.

Order: A and B in parallel, then C, then D (D can start against the payload shape above).

## Verification

- Unit tests per slice; full suite within the 0.0007 s per test budget.
- Live: `/cheapest` for Tritium near the current system returns hub rows within a second and Spansh rows after; carriers hidden with a count; switching `node=` uses the peer's ship pad and cargo.
