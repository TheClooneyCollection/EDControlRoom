# 0016: Journal Events on the Hub and a Fitted Trip Time

## Status

Designed (2026-11-13). Built: step 1 (store and local sync, 2026-11-13), step 2 (peer sync, 2026-11-13).

## Why

`/routes` and Best deal rank routes by profit per hour, and the trip time comes from a hand-fitted `TimeModel` (`[eddn.time_model]`, `defaults/eddn.toml`). It drifts from how the pilot actually flies (about 13 to 25s per leg optimistic on 2026-11 haul legs), and refitting it is a manual job.

Each machine's journal stays on that machine. The hub sees only haul runs (no `FSDJump`, no interruptions) and station facts, so it cannot fit the model, and every journal-based view (the `All trading (journal)` ledger, balance estimates) is local only.

Goal: every node's journal events end up in one database on the hub, and the trip time can be fitted from them. A config page shows the configured values and the fitted values side by side; the player edits the configured ones and picks which set is used.

## Decisions (confirmed with the user)

- Sync every journal event except chat and friends: `ReceiveText`, `SendText`, `Friends` are never stored or sent.
- Backfill the whole journal history on the first sync (the Mac had 19 MB in 168 files over six months).
- The config page writes `config.toml` and the change applies live, without a server restart.
- Fitted values use the last 14 days of events by default.
- The configured values are the starting point: the active set is `config` until the player switches to `fitted`.
- Fit per ship (by `ShipID`): `fitted` means the values fitted for the ship the viewed node is flying now. On 2026-05..11 Mac journals the Panther Mk II took 383s for a 1-jump leg to a 300 Ls orbital station against 326s in the Caspian Explorer (17% slower), and one pooled fit was off by about 15s per leg for both.

## Design

### Journal event store

Hub and standalone open one more SQLite file, `[hub] journal_events_file` (default `.control_room_journal.sqlite3`, git-ignored), separate from the market DB, which prunes by age.

```sql
CREATE TABLE journal_event (
    node_id TEXT NOT NULL,
    file TEXT NOT NULL,       -- journal file name, e.g. Journal.2026-11-11T060032.01.log
    line INTEGER NOT NULL,    -- 1-based line in that file
    timestamp REAL NOT NULL,
    event TEXT NOT NULL,
    body TEXT NOT NULL,       -- the JSON line as written
    PRIMARY KEY (node_id, file, line)
) WITHOUT ROWID;
CREATE INDEX journal_event_time ON journal_event (event, timestamp);
```

Inserts are `INSERT OR IGNORE`, so a line sent twice is stored once. Lines that are not valid JSON (a torn last line) are not stored and are read again on the next scan.

### Reading the journal

A server thread `journal-sync` scans the journal directory (`ctx.journal.effective_path`) every few seconds, independent of the routines' journal tailing so it also sees files from before this launch:

- Per file it remembers how many complete lines it has passed on (`[hub] journal_sync_file`, default `.control_room_journal_sync.json` on the node: file name to line count). A file that grew is read from that line on; a new file from the start. Files are handled oldest first.
- A line is complete only when it ends with a newline.
- Hub and standalone write the lines straight into the store under their own node id. A peer queues them in its outbox.

### Peer to hub

A new outbox item kind `journal_events`: `{file, first_line, lines: [...]}` with up to 500 lines or 512 KB per item, key `journal:<file>:<first_line>` (kept forever, like haul runs). The hub stores them under the peer's node id and acknowledges as usual. The peer's sync state advances when the item is queued, not when the hub acknowledges it, since the outbox already keeps it until then. The first link backfills the whole history through the outbox.

### Fitting the trip time

`edcr/trip_time_fit.py` reads the store, so the fit covers every node:

- **Legs**: `Undocked` to the next `Docked` on the same node. Jumps are the `FSDJump` events between them; `DistFromStarLS` and `StationType` come from the `Docked`. Docked time is `Docked` to the next `Undocked`.
- **Dropped**: a leg containing `Died`, `Interdicted`, `EscapeInterdiction`, `Touchdown`, `Shutdown`, `LoadGame`, `Resurrect` or more than one `SupercruiseExit`; a leg longer than 30 minutes; a docked stop longer than 10 minutes.
- **Fit**: least squares of leg time on `travel_base_s`, `first_jump_s` (1 when it jumped), `per_extra_jump_s` (jumps - 1), `supercruise_coeff` (Ls^(1/3)) and `surface_extra_s`, then legs off by more than max(60s, 3 × MAD) are dropped and it is fitted again. A field with fewer than 10 supporting legs (for example no multi-jump legs) keeps its configured value and is not fitted. `docked_s` is the median docked stop. Fitted values are clamped at zero.
- **Per ship**: each leg and docked stop belongs to the `ShipID` of the latest `Loadout` or `LoadGame` before it on that node. The ship's own legs are fitted; with fewer than 30 legs the pooled fit of every ship is used instead, and with fewer than 30 pooled legs the configured values.
- Only the last `fit_days` (default 14) count. The fit is cached and refreshed when new events arrive, at most once a minute.

On the 2026-11-10..13 haul runs a prototype found 184 legs, with only 8 two-jump legs, so `per_extra_jump_s` would stay configured.

### Config and the active set

```toml
[eddn.time_model]
source = "config"   # "config" or "fitted"
fit_days = 14
docked_s = 90.0     # the configured values, as today
...
```

`source = "fitted"` uses the values fitted for the viewed node's current ship (a peer's route request to the hub carries its `ShipID`); a field the fit could not fit uses the configured one. `/api/eddn-routes` and Best deal read the active model on every request and say which it was: configured, fitted for this ship, or pooled.

### Config page

A new page `/config` (sidebar link), first section **Trip time**:

| Field | Configured (editable) | Fitted (current ship) | Legs |
|---|---|---|---|

- A switch **Use: Configured / Fitted** writes `source`.
- **Save** writes the configured values to `config.toml` (the same way `save_home_system` edits it) and applies them live.
- Under the table: which ship (or pooled) the fit is for, how many legs and docked stops it used, over which window, and which fields kept the configured value.
- `GET /api/time-model` returns both sets, the fit counts and the source; `POST /api/time-model` saves. On a peer the page asks the hub, as other hub-owned data.

`/routes` and Best deal say under the results which set the trip time came from.

## Build steps

Each step lands on `main` with tests and works on its own.

1. **Store and local sync**: journal event store, `journal-sync` thread on hub and standalone, chat filter, sync state, full backfill. A small CLI check: `tools/journal_events.py` counts events per node and event.
2. **Peer sync**: `journal_events` outbox items, hub storage under the peer's node id, backfill over the link.
3. **Fit**: `edcr/trip_time_fit.py` on the store, `[eddn.time_model] source` and `fit_days`, active model in `/api/eddn-routes` and Best deal, `GET /api/time-model`.
4. **Config page**: `/config` with the Trip time section, `POST /api/time-model` writing `config.toml` and applying live, source line on `/routes` and Best deal.
5. **Docs**: `docs/user/trade-routes.md`, `docs/user/hub.md`, status.

## Open points

- Other journal views (the `All trading (journal)` ledger, balance) could read the store later so the hub sees every node; not part of this plan.

## Validation

- Unit tests: incremental scan (grown file, new file, torn last line), chat filter, idempotent store, peer items and hub storage over the in-memory link, leg extraction and drop rules, fit with missing support keeping configured values, config save and live apply.
- Live: backfill the Mac's history, connect the Windows peer and check its events reach the hub, compare fitted and configured trip times against a few real haul loops.
