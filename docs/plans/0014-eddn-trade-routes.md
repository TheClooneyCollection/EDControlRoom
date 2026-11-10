# 0014: EDDN Trade Routes

## Status

In progress: slices 1 and 2 (listener, store, `tools/eddn_listen.py`) are built. Phase 1 below; "Good Deals / Exceptional Routes" alerts are a later phase.

## Why

Route search today scrapes Inara through Playwright (`edap/inara/trade_routes.py`). It is slow, depends on a browser, ranks by Inara's undocumented profit model, and only searches near one system. EDDN publishes every market snapshot players upload, so a local listener can keep a current price table and rank routes ourselves:

- near the current location (default view), and
- anywhere in the galaxy (global view), so we learn where the good routes are even when we are not there.

Goal: plan the next haul. No price history is needed; the latest snapshot per market is enough.

## Scope (phase 1)

### 1. EDDN listener

- New module `edap/eddn/listener.py`: ZMQ SUB to `tcp://eddn.edcd.io:9500`, zlib-decompress, JSON-parse, dispatch by `$schemaRef`.
- Handle `commodity/3` (market prices), `journal/1` `Docked` (station type, distance to arrival, pads, services, market id) and `journal/1` `FSDJump` / `Location` (system coordinates).
- Runs in a background thread inside the Control Room server on the Mac. Reconnects on drop; logs message rate and last-message age for the diagnostics surface.
- New dependency: `pyzmq`.

### 2. SQLite store, latest snapshot only

`eddn.database_file` (default git-ignored repo-root `.eddn_markets.sqlite3`), WAL mode, writes committed about once a second.

- `system(address PK, name, x, y, z, updated_at)`
- `station(market_id PK, system_address, name, type, dist_ls, max_pad, is_carrier, is_surface, updated_at)`
- `market(market_id PK, updated_at)`
- `price(market_id, commodity, buy, sell, supply, demand, PRIMARY KEY (market_id, commodity)) WITHOUT ROWID`

A new `commodity/3` message for a market replaces all its `price` rows in one transaction. A periodic prune drops markets not updated for `eddn.max_age_days` (default 7). Fleet carriers are stored (flag `is_carrier`) but excluded from routes by default; their markets move and empty quickly.

### 3. On-demand Ardent lookups

When a station or system in a candidate route lacks coordinates, pad size or distance-to-arrival, fetch it from Ardent Insight API on demand and cache it in the same tables. No bulk import in phase 1.

### 4. Route finder

- Two-station round trips (A buys X sells at B, B buys Y sells at A; one-sided allowed), using the same shape as `TradeRoute` so a found route can be selected and run by the existing haul flow.
- Pair candidates through a spatial grid with cell size = search range. Cost grows roughly with range cubed until it covers the whole bubble, so the global view is computed in the background on an interval and cached; the near view is computed on request.
- Filters: cargo capacity, pad size, max station distance (ls), min supply / demand, carriers excluded, surface stations opt-in. Defaults come from the current ship `Loadout` and `haul_search.toml`.

### 5. Ranking: profit per hour

Every route is ranked by estimated profit per hour, not profit per trip. Jump count is part of the time, so a multi-jump route ranks high only when its profit pays for the extra flying.

- One leg ≈ `undock_and_launch + jumps × per_jump + supercruise(dist_ls) + dock_and_trade`.
- `jumps = ceil(distance_ly / laden_jump_range)`. Laden range comes from `Loadout`: `MaxJumpRange × (UnladenMass + one-jump fuel) / (UnladenMass + FuelCapacity.Main + CargoCapacity)`. For the current Panther Mk II this gives 17.19 ly, matching `max_route_distance_ly = 17.2` in `haul_search.toml`.
- Calibrate the constants from `.control_room_haul_runs.jsonl` (completed runs, median durations; e.g. Voltaire Terminal ↔ Melroy Gateway, 41 runs, median 816s round trip). Supercruise time is fitted against `dist_ls`; per-jump time starts at ~50s and is refined once multi-jump runs exist.
- Show jumps and estimated trip time on every route so the ranking is explainable.

### 6. `/routes` web page

- Two tabs: **Near** (around the current system, default) and **Global** (top N anywhere, with the time it was last computed).
- Range presets reuse the `/haul` preset style, but measured in laden jumps: `1 jump`, `2 jumps`, `4 jumps` (default, ~69 ly for the current ship), plus the existing 100 ly+ presets for wide searches. The range is a search limit; ranking does the rest.
- Each row: stations, systems, commodities each way, profit per trip, profit per hour, jumps, est. trip time, data age. Buttons to select the route for haul and to set the destination, like `/haul`.
- Header: listener state, messages per minute, markets stored, oldest/newest data.

## Later

- **Good Deals / Exceptional Routes**: alert (TTS and web) when a route beats the current haul or a profit/hour threshold, or a price is far outside its usual range.
- Multi-leg loops (A→B→C→A) from the same table, feeding `/multi-haul`.

## Open points to confirm while building

- Exact Ardent endpoints and rate limits.
- Global recompute interval (start with 10 minutes) and top N (start with 50).
- Whether Inara search stays as a fallback once `/routes` is trusted.

## Validation

- Unit tests with recorded EDDN payloads (parse, upsert, replace, prune) and a small synthetic galaxy for the route finder and time model.
- Live: run the listener for an hour, compare a few stations against Inara, and check that the current Voltaire ↔ Melroy route ranks near the top of the Near view with a trip time close to 816s.
