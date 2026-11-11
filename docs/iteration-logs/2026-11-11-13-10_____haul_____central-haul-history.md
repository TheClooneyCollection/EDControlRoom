# Iteration Log

- Area: `haul`
- Title: `central-haul-history`
- Started: `2026-11-11 13:10`

## Summary

- Plan 0015 step 4: a peer sends every finished haul run (completed or aborted) up the link through its outbox; the hub keeps every node's runs and its haul page History panel, `/api/haul-stats` and Best deal's measured profit per hour read the central history, with node and ship filters. A peer's history views and measured profit per hour come from the hub.

## Changes

- Peer: the server watches `control_room.haul_runs_file` (5 s mtime poll, like the recent-markets watcher, now the generic `recent_markets.watch_file`) and calls `PeerLink.enqueue_runs(load_runs(path))`. Item kind `haul_run`, key `run:<started_at>|<ended_at>|<station_1>`. Run keys go in a new outbox table `kept` that never expires (`Outbox.add(..., forever=True)`), so the rescan at every start queues only new rows and the first link backfills the whole file once; market and fact keys still expire after 30 days. The file stays the peer's source of truth.
- Hub storage: a JSONL file, `[hub] runs_file` (default `.control_room_hub_runs.jsonl`, git-ignored), each row the peer's row plus `node: {id, name}` (`edap/hub/history.py` `HubRuns`). Chosen over a market DB table: same format as `haul_runs_file`, so `load_runs`/`summarize`/`measured_route` and `tools/haul_stats.py --file` work unchanged, append + fsync as today, and it keeps history out of the EDDN store (its own writer thread, pruning and size). Dedupe: an in-memory key set loaded at open; `run_key` (in `haul_history`) is now `(started_at, ended_at, station_1, node id)` and `load_runs` dedupes by it. A row that is not a finished run is acked with an error and dropped; a failed append nacks (kept on the peer).
- The hub's own runs are not copied: `CentralHistory.rows()` reads its `haul_runs_file`, tags each row with the hub's node id and name, then adds the peer rows (any peer row claiming the hub's id is ignored).
- `ItemSink` now takes the sending node (`store_item(node, kind, body)`); `store_link_item(store, runs, log)`. `HubSide` gains `history`.
- `/api/haul-stats?window=&node=<id|all>&ship=<id|all>` (bad ship 400) adds `node`, `ship`, `nodes` (hub only, local first), `ships` and `journal_node`. The journal ledger is this machine's own journals, shown for node `all` or this machine's node, else null. A peer asks the hub (`haul_stats` request), tags the answer `hub`, adds its own ledger; 502 with "Hub X is unreachable" when away.
- Best deal measured: hub over every node's runs for the current ship; a peer sends `measured` (`stations` by name and system, `ship_id`, `window`) and shows `measured_hint` when the hub is away or refuses. `trade_trip.StationName` names a station for `measured_route`.
- Web: History panel gets node and ship selects (hidden until there are two to pick, remembered per browser), status says "(from hub X)", journal line names the machine. `markets.js` shows `measured_hint`.
- Live smoke (hub and peer as two local `serve` processes on loopback, temp configs): backfill of 2 peer rows, filters by ship and node, new peer run appears in 5 s, peer restart sends 0 items, hub away gives 502 and a queued run, hub back drains it. Haul page checked headless at 1280 and 390 px: filters show, no horizontal scroll, no page errors.

## Follow-ups

- `stats` command and TUI "Today" line still read the machine's own file.
- Ship ids are per commander: two commanders on different nodes can share a ship id, and the ship filter would merge them.
- A peer moved to a different hub does not resend history (keys are kept forever); deleting the outbox file backfills again.
