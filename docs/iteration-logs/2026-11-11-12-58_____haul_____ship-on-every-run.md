# Iteration Log

- Area: `haul`
- Title: `ship-on-every-run`
- Started: `2026-11-11 12:58`

## Summary

- Plan 0015 step 3: every haul run row records its ship, and Best deal's measured profit per hour counts only completed runs on the pair for the current ship over a picked window (48h, 7 days default, 30 days, all).

## Changes

- Ship identity: `ShipState` (`edap/control_room/models.py` and `edap/state.py`) gains `ship_id`, `ship_name`, `ship_ident` from `LoadGame`/`Loadout` (`apply_ship_identity`); carried through bootstrap, the local data source copy, the connect client and the data message parser.
- Run rows: `haul_tracking.ship_record` stores `ship` = `{id, type, name, ident, cargo_capacity, max_jump_range_ly, laden_jump_range_ly}` on the current run. Set on the first recorded event, or later while the id is still unknown (a run saved before this change, or begun before the Loadout). Old rows without `ship` load unchanged.
- Laden range: `ControlRoomApp._laden_jump_range_ly` calls the existing `route_query.laden_jump_range` with `haul_search.toml` (max route distance, else 17.2 Ly). There is no laden formula from ship mass in the code; this is the value `/routes` and Best deal already use.
- `parse_window` accepts `7d` and `30d` (elapsed, like `48h`); `stats` takes them too.
- `trade_trip.measured_route(rows, x, y, *, ship_id, since, until)` filters raw rows (completed, ended in window, pair either direction with the same system check, ship id match or unknown) and returns runs, profit, duration, profit/hour, `loop_s`, `unknown_ship_runs` and the newest known run's `laden_jump_range_ly`. With no current ship id every run counts.
- `/api/market-compare?window=48h|7d|30d|all` (default `7d`, else 400) adds `measured_window` and `measured_ship`; the current ship is the server's live `ship`.
- `web/markets.js`: a window select inside the Measured per hour block (remembered in localStorage), note with run count, loop time, ship, recorded laden range with today's beside it when different, and "n ship unknown".
- Checked the page headless (Playwright, desktop 1280 and phone 390): no horizontal scroll, no page errors, window switch refetches.

## Follow-ups

- Step 4 sends runs to the hub; a peer's measured profit per hour uses its own history until then.
- Haul page history does not show the ship per route yet (optional in the step).
- The recorded laden range is the configured one, so it only reflects a better ship if `haul_search.toml` is updated.
