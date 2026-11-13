# Iteration Log

- Area: `hub`
- Title: `journal-event-store-and-sync`
- Started: `2026-11-13 18:01`

## Summary

- Wrote [plan 0016](../plans/0016-journal-events-and-trip-time-fit.md): every node's journal events go into one store on the hub, and the trip time is fitted from them per ship. A `/config` page shows configured and fitted values side by side, with a switch between the two sets.
- Per-ship check on 2026-05..11 Mac journals (497 clean legs): for a 1-jump leg to a 300 Ls orbital station, the Panther Mk II took 383s against 326s in the Caspian Explorer. A pooled fit was off by about 15s per leg for both, so the fit is per `ShipID`.
- Built step 1: the store and local sync on hub and standalone.

## Changes

- `edcr/journal_store.py`: `JournalStore`, one row per `(node_id, file, line)` with timestamp, event and the raw line, `INSERT OR IGNORE`. `ReceiveText`, `SendText` and `Friends` are never stored.
- `edcr/journal_sync.py`: reads `Journal.*.log` oldest first from the saved line and byte position. Only newline-terminated lines count, in batches of 500 kept lines, and the position is saved per batch. `sync_journal_every` runs it as the `journal-sync` thread (5s).
- `[hub] journal_events_file` (`.control_room_journal.sqlite3`) and `journal_sync_file` (`.control_room_journal_sync.json`), both git-ignored. `serve.py` starts the sync when the role owns data; standalone gets a node id from the shared node id file.
- `tools/journal_events.py`: events per node and event.
- Live backfill of the Mac journals into a scratch store: 64,339 events in 168 files in 0.8s, 35 MB; a second pass took 1ms and stored no chat.

## Follow-ups

- Step 2: `journal_events` outbox items from peers, stored under the peer's node id.
