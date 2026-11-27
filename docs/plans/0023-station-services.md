# 0023: Nearest Station With a Service

## Status

Decisions confirmed 2026-11-27; not built. Mission M8.

## Why

"Where is the nearest Fleet Carrier Administration (or Fleet Carrier Vendor, Material Trader, ...) to system Y?" takes Spansh in a browser today. EDDN journal `Docked` and `Location` messages carry `StationServices`, but `_station_info` (`edcr/eddn/messages.py`) drops it, so the hub store cannot answer.

## Findings (2026-11-27)

- Local journals show `StationServices` as lower-case symbols with a few camel-case ones (`stationMenu`, `techBroker`). Carrier ones seen: `carriermanagement`, `carrierfuel`. `carriervendor` is not in local journals; slice A confirms the EDDN spelling from a live message before fixing the label table.
- Spansh `POST /api/stations/search` filters by service with `"filters":{"services":[{"name":"Fleet Carrier Administration"}]}` and sorts with `"sort":[{"distance":{"direction":"asc"}}]` from `reference_system`. The `{"value":[...]}` shape is ignored silently (returns everything). Galaxy-wide counts: Fleet Carrier Administration 393, Fleet Carrier Vendor 13, Material Trader 1635, Technology Broker 9939; Interstellar Factors Contact, Black Market, Shipyard and Outfitting all hit the 10000 cap.
- Spansh rows carry `market_id`, `name`, `type`, `system_name`, `distance`, `distance_to_arrival`, `large_pads`/`medium_pads`/`small_pads`, `has_large_pad`, `updated_at`, and `services[]` as `{"name": ...}`. Carriers are included (they list `Fleet Carrier Fuel`).
- Hub store: 64,700 stations, 444k systems with coordinates, no services anywhere. The snapshot import checks `user_version == 1` exactly and copies `station` with `SELECT *`.
- Ardent station rows and `StationTypeSeen` also write `station` and know no services.

## Decisions (confirmed with the user)

- Surface: hub API plus a new `/services` page, linked in the nav. Same `node=` rule as `/cheapest`: the hub answers, peers forward.
- Backfill: like M7. Hub rows first, one Spansh search per query fills in, rows merge by `market_id`, newer services timestamp wins, each row marked `hub` or `spansh`. A Spansh failure keeps the hub rows and shows the error.
- Scope: store the full `StationServices` list from every Docked/Location. The page offers a short list (Fleet Carrier Administration, Fleet Carrier Vendor, Interstellar Factors, Material Trader, Technology Broker, Shipyard, Outfitting, Black Market); the API accepts any symbol. A symbol with no Spansh name skips Spansh and says so.
- VPS: the hub must import old and new snapshots, so deploy order does not matter. The plan lists the VPS step; nobody touches the VPS without the user's go.
- Defaults (following M7, not asked separately): carriers excluded with a count and a toggle (carriers move, so their services go stale fast); pad from the viewed node's ship; reference system = its current system; radius 200 ly, clearable; no age limit (services rarely change), age shown per row.

## Rejected

- A `services` column on `station`: v1 snapshots would no longer import with `SELECT *`, and Ardent or `StationTypeSeen` writes would need care not to wipe it. Separate tables avoid both.
- Bumping `SCHEMA_VERSION`: the change is additive, so it is not needed (see Store).
- Ramp-up only: about 400 FC Administration stations galaxy-wide; most would stay unknown for weeks.
- One-off Spansh seed: goes stale and needs its own job; per-query Spansh stays fresh.
- A mode inside `/cheapest`: its controls are commodity-shaped.

## Design

### Store (`edcr/eddn/store.py`, `edcr/eddn/messages.py`)

New tables, created with `CREATE TABLE IF NOT EXISTS` in `_SCHEMA`; `SCHEMA_VERSION` stays 1:

```sql
CREATE TABLE IF NOT EXISTS station_services_seen (
    market_id INTEGER PRIMARY KEY,
    updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS station_service (
    service TEXT NOT NULL,          -- lower-cased symbol: "carriermanagement"
    market_id INTEGER NOT NULL,
    PRIMARY KEY (service, market_id)
) WITHOUT ROWID;
```

- `StationInfo` gains `services: tuple[str, ...] | None` (`None` = message had no list; Ardent and `StationTypeSeen` pass `None`). `_station_info` lower-cases and dedups the list.
- `_apply_station` keeps its row logic; then, when `services is not None` and the timestamp is at least `station_services_seen.updated_at`, it replaces that station's `station_service` rows and upserts `station_services_seen`. This is newest-wins on its own clock, so a newer Ardent row never wipes services.
- `import_database`: if the snapshot has `station_services_seen` (check `snapshot.sqlite_master`), take rows newer than ours, replace their `station_service` rows, and add `services` to `SnapshotImport`. A v1 snapshot without the tables imports as before. An old hub importing a new snapshot ignores the extra tables.
- `prune` leaves services alone; they belong to stations, not markets.

### Query module (`edcr/station_services.py`)

```python
SERVICE_LABELS: dict[str, str]     # "carriermanagement" -> "Fleet Carrier Administration"; also the Spansh name
PAGE_SERVICES: tuple[str, ...]     # the page's short list, in order

@dataclass(frozen=True)
class ServiceQuery:
    service: str                   # lower-case symbol
    reference_system: str          # required
    radius_ly: float | None        # None = galaxy-wide
    pad: str                       # "S" | "M" | "L"
    include_carriers: bool
    use_spansh: bool
    limit: int                     # 50

@dataclass(frozen=True)
class ServiceStation:
    source: str                    # "hub" | "spansh"
    market_id: int
    system_name: str
    station_name: str
    station_type: str
    is_carrier: bool
    max_pad: str                   # "" unknown
    dist_ls: float | None
    distance_ly: float
    services_at: float             # epoch seconds the services list was seen

def parse_service_query(params: Mapping[str, str], *, current_system: str, ship_pad: str) -> ServiceQuery
def query_hub_services(db: Path, query: ServiceQuery, origin: tuple[float, float, float]
                       ) -> tuple[list[ServiceStation], dict[str, int]]   # hidden counts: carrier, pad, radius
def merge_stations(hub: list[ServiceStation], spansh: list[ServiceStation], query: ServiceQuery) -> list[ServiceStation]
def services_payload(...) -> dict[str, Any]
```

Reuse from M7: `PAD_ORDER`, `hub_system_coordinates`, and `lookup_system_coordinates` (unknown reference: Spansh coordinates when `use_spansh`, else 404 "Unknown system"). Sort by `distance_ly`, then `dist_ls`. A Spansh row wins a `market_id` tie only when its `updated_at` is newer; the hub's `max_pad` fills in when Spansh pad counts are missing.

Spansh (`edcr/spansh_stations.py` gains `search_service(query, spansh_name, post, origin) -> tuple[list[ServiceStation], int]`): one request, `size` 50, services filter, distance sort, `distance` range when a radius is set, `type` allow-list `NON_CARRIER_TYPES` unless carriers are included. Pad from `large_pads`/`medium_pads`/`small_pads`.

### HTTP and hub

`GET /api/nearest-services?service=carriermanagement&system=Adach&radius_ly=200&pad=L&carriers=0&spansh=1&node=<id>`. Payload:

```json
{"service": "carriermanagement", "label": "Fleet Carrier Administration", "query": {...},
 "stations": [{...ServiceStation..., "age_s": 3600}],
 "hidden": {"carrier": 3, "pad": 12, "radius": 40},
 "hub_known": 51234,
 "spansh": {"asked": true, "count": 393, "error": ""}}
```

`hub_known` is how many stations have a services list at all, so the page can say "hub knows services for 51,234 stations" while coverage ramps up. `REQUEST_NEAREST_SERVICES = "nearest_services"` in `edcr/hub/protocol.py`, routed like `REQUEST_CHEAPEST_MARKETS` (peer forwards, hub runs store and Spansh, same search timeout).

### Page (`web/services.html`, `web/services.js`, `web/nav.js`)

Form: service (short list plus free text), system, radius, pad, carriers toggle, Spansh toggle. Table: station, system, distance ly, arrival Ls, pad, type, services age, source. Hidden counts line, coverage line, Spansh status line. Carrier rows carry a badge.

## Slices (by file ownership)

- A: `edcr/eddn/messages.py`, `edcr/eddn/store.py`, `edcr/ardent.py` (pass `services=None`), tests in `tests/test_eddn_store.py` and `tests/test_eddn_messages.py`. Include: services newest-wins, Ardent row does not wipe services, v1 snapshot without the tables imports, snapshot with tables merges. Confirm the `carriervendor` spelling from a live EDDN message.
- B: `edcr/station_services.py`, `edcr/spansh_stations.py` `search_service`, `tests/test_station_services.py`. Injected `PostJson`, no network. Depends on A's tables (build fixtures with `EddnStore`).
- C: `edcr/hub/protocol.py`, `edcr/control_room/server/app.py` endpoint, page route and `services.js` MIME entry, `tests/test_control_room_services.py`. Depends on B.
- D: `web/services.html`, `web/services.js`, `web/nav.js`. Can start against the payload above.

Order: A, then B and D in parallel, then C.

## Deploy

1. Hub: normal update. New tables are created on open; existing data is untouched.
2. VPS listener: same code update so its snapshots carry services. Only with the user's go; follow the stop-and-restart notes for the VPS listener. Until then the hub's services come from its own listener and Spansh.

## Verification

- Unit tests per slice; full suite within 0.0007 s per test.
- Live: `/services` for Fleet Carrier Administration near the current system shows Spansh rows at once and hub rows as docks arrive; the coverage line grows; carriers hidden with a count; `node=` uses the peer's ship pad and system.
