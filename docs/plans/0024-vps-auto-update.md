# 0024: VPS Auto-Update of the EDDN Listener

## Status

Decisions confirmed 2026-11-27; not built. Mission M9. Spans this repo and the ansible repo that owns the `edcr_eddn_listener` role.

## Why

The VPS listener only moves when someone runs the ansible role by hand, so it drifts behind `main` (18 commits at the time of writing). Every commit on `main` should reach the VPS on its own, with schema migrations and a way back when a commit breaks the listener.

## Findings (2026-11-27)

- The role clones the repo into a root-owned checkout at `edcr_eddn_listener_version` (`main`), runs `uv sync --frozen --no-dev` as the service user into a venv in the state dir, and runs `edcr-eddn-listen.service` (`uv run --no-sync python3 tools/eddn_listen.py --db ...`, `Restart=on-failure`, `RestartSec=10`). `edcr-market-snapshot.timer` writes a snapshot hourly from the same checkout.
- git as a non-root user hits "dubious ownership" on the checkout, so the updater runs as root.
- `edcr/eddn/store.py`: `SCHEMA_VERSION = 1`; `__init__` runs `_SCHEMA` (all `IF NOT EXISTS`) and sets `user_version` only when it is 0. Nothing upgrades an older database.
- Snapshot checks require an exact match: `write_snapshot` accepts a source at 0 or `SCHEMA_VERSION` (`market_snapshot.py:52`), `read_manifest` requires `schema == SCHEMA_VERSION` (`:109`), `import_database` requires the attached `user_version == SCHEMA_VERSION` (`store.py:203`). The hub shows a rejected snapshot in the snapshot refresh `error` field and logs a warning.
- Every push to `main` runs the `Tests` workflow; the repo is public, so its result is readable without a token.
- No Discord webhook exists in the ansible repo or its vault. The only one is the `DISCORD_WEBHOOK_URL` GitHub secret.

## Decisions (confirmed with the user)

- Track `main`: once a commit lands and its `Tests` run passes, the VPS pulls, migrates and runs it. No manual step.
- Trigger: a systemd timer on the VPS, every 10 minutes. No GitHub secrets, no SSH from Actions.
- CI gate: deploy only the `main` tip whose `Tests` run concluded `success`. Pending: wait for the next tick. Failed: skip it and wait for a newer tip.
- Safety: smoke check before restart; if the listener does not come up after restart, roll back to the previous commit (and the pre-migration database when a migration ran), re-sync, restart.
- Notifications: off for now (no webhook). The updater logs every outcome to its journal. The notifier is built with an empty-by-default webhook setting; once one is set, it posts on every update, skip and rollback.
- Migrations: a `user_version` ladder in `edcr/eddn/store.py`, run in `EddnStore.__init__` before serving, with a database backup before the first step. Additive changes (new tables, like M8) keep using `IF NOT EXISTS` and do not bump the version, so bumps stay rare.
- Version skew: the VPS updates within minutes, the hub by hand. The hub imports snapshots at or below its version (migrating the downloaded copy first) and rejects newer ones with "VPS snapshot schema N is newer than this hub (M); update the hub" in the refresh error. Until the hub is updated it runs on its own listener and Spansh.

## Rejected

- Updater inside this repo: a broken commit could break its own rollback. The updater lives in the ansible role and runs on the system `python3`, stdlib only.
- Migrating while the old listener still runs: the old code would write into the new shape. The listener is stopped across the restart.
- Rollback without restoring the database: after a non-additive migration the old code cannot use the new shape, and the new code refuses a newer `user_version` anyway. Losing a few minutes of EDDN data on rollback is fine.
- Holding back commits that bump `SCHEMA_VERSION` until a manual go: breaks "no manual step".
- Ansible and the timer both moving the checkout: they would race. After the first clone only the updater moves it.

## Design

### Store migrations (`edcr/eddn/store.py`)

```python
SCHEMA_VERSION = 1
# MIGRATIONS[n] upgrades a version-n database to n + 1. Each step is written against the version-n shape, not _SCHEMA.
MIGRATIONS: dict[int, Callable[[sqlite3.Connection], None]] = {}

def migrate(db: sqlite3.Connection, *, target: int, migrations: Mapping[int, Callable[[sqlite3.Connection], None]],
            backup: Callable[[int, int], None]) -> int   # returns the starting version
def migrate_file(path: Path) -> None                     # snapshot copies: no backup
```

`EddnStore.__init__(connection, *, backup)` order:

1. Read `user_version`. Above `SCHEMA_VERSION`: raise `ValueError("Market database schema N is newer than this code (M)")`.
2. 0 with no tables: run `_SCHEMA`, set `SCHEMA_VERSION`, done. 0 with tables (a store from before the version existed): treat as 1.
3. Below `SCHEMA_VERSION`: call `backup(from, to)` once, then run each step in its own transaction that also sets `user_version = n + 1`.
4. Run `_SCHEMA` for additive tables and indexes. It runs after the ladder because an index in the latest `_SCHEMA` may name a column an old table does not have yet.

`EddnStore.open(path)` passes a backup that writes `VACUUM INTO <db>.pre-v<to>` next to the database and then deletes older `<db>.pre-v*` files, so at most one backup is on disk. Tests pass their own `backup`; production callers always pass one (no default). The hub's own store gets the same protection.

### Snapshots (`edcr/market_snapshot.py`)

- `read_manifest`: accept `1 <= schema <= SCHEMA_VERSION`; newer raises the "update the hub" message above.
- `fetch_and_import`: after download, `migrate_file(path)` when the copy is older, then `import_database` (its exact check stays).
- `write_snapshot`: unchanged. The listener has migrated the source before the snapshot timer runs again.

### Smoke check (`tools/eddn_listen.py --check`)

Imports the listener, store and snapshot modules, opens the database read-only (`mode=ro`, missing file counts as 0), prints `schema db=<x> code=<y>` and exits 0, or exits 1 when `x > y` or anything fails to import. It never writes. The updater reads the line to know whether a migration (and so a backup) will happen.

### Updater (ansible repo, `roles/edcr_eddn_listener`)

`files/edcr_auto_update.py`, run by `edcr-auto-update.service` (oneshot, root, `After=network-online.target`) from `edcr-auto-update.timer` (`OnBootSec=5min`, `OnUnitInactiveSec=10min`, `RandomizedDelaySec=60`). Settings come from a rendered `/etc/edcr-auto-update.env` (repo slug, ref, checkout, venv, db, service user, unit names, CI workflow name, health timeout, webhook, mode 0600). State (deployed, previous, last rejected commit) lives in a small JSON file under the role's state dir. One run, holding `flock` on a lock file:

1. `git fetch origin <ref>`; target = `FETCH_HEAD`. Same as `HEAD`, or the last rejected commit: exit.
2. CI gate: `GET /repos/<slug>/actions/runs?head_sha=<target>&event=push`, pick the `Tests` run. Missing or running: exit. Not `success`: record rejected, log, exit.
3. `git reset --hard <target>`, `uv sync --frozen --no-dev` as the service user, `tools/eddn_listen.py --check`. Failure: reset to the previous commit, re-sync, record rejected, exit. The listener was never stopped.
4. Stop `edcr-market-snapshot.timer` and wait for its service to finish. Restart the listener.
5. Health: within the health timeout (default 600 s, a migration and backup can take minutes) the listener's journal since the restart shows `Listening to`, and 30 s later it is still `active` with the same `MainPID` and `NRestarts`.
6. Unhealthy: stop the listener; if `--check` reported a migration, move `<db>.pre-v<to>` back over the database and drop its `-wal`/`-shm`; reset to the previous commit; re-sync; restart; health check again; record rejected. If the rollback is also unhealthy, log it loudly and leave systemd's restart loop running.
7. Start the snapshot timer again, write state, notify (no-op while the webhook is empty).

Every step goes through injected `run`, `http_get`, `sleep` and `now` functions so it is unit-tested without git or systemd.

### Role changes

- Defaults: `edcr_eddn_listener_auto_update: true`, `..._auto_update_interval: 10min`, `..._auto_update_ci_workflow: Tests`, `..._auto_update_health_timeout_s: 600`, `..._auto_update_discord_webhook: ""` (vault when set).
- "Check out EDControlRoom" only clones when the checkout is missing (`update: false` otherwise). After deploying the units, the role runs `systemctl start edcr-auto-update.service`, so a manual ansible run updates through the same path and lock. `edcr_eddn_listener_version` stays the single ref both use; pinning a tag still works.
- `ansible-node-plan.md` and the role notes describe the timer and how to pause it (`systemctl disable --now edcr-auto-update.timer`).

## Slices (by file ownership)

- A (this repo): `edcr/eddn/store.py` (`__init__`, `open`, `MIGRATIONS`, `migrate`, `migrate_file` only), `edcr/market_snapshot.py`, `tools/eddn_listen.py --check`, new `tests/test_eddn_store_migrations.py`, additions to `tests/test_market_snapshot*.py` and `tests/test_eddn_listen.py`. Tests use fake ladders (no real step exists yet): v0 store upgrades to 1, steps run in order with one backup, a failing step leaves the old version, a newer database raises, an older snapshot imports, a newer manifest gives the "update the hub" message.
- B (ansible repo): updater script, its unit test, the two units, env template, defaults, tasks, docs. Built against the `--check` contract in parallel with A. Validate with `--syntax-check`, `scripts/lint.sh` and the unit test.

M8 seam: M8 slice A edits `_SCHEMA`, `_apply_station` and `import_database` in `store.py`; M9 slice A edits only `__init__` and `open` and adds new functions, so rebasing either onto the other is trivial. Land M9 A after M8 A if both are open; M8's tables stay additive and do not bump `SCHEMA_VERSION`.

## Deploy

1. Slice A on `main`. With no steps in the ladder it changes nothing at runtime. The hub picks up the version window on its next manual update.
2. Slice B in the ansible repo.
3. With the user's go only: run the role on the VPS with `--check --diff`, then for real with `--tags edcr_eddn_listener`. The first run moves the listener straight to the `main` tip, which must include slice A for `--check`. Watch `journalctl -u edcr-auto-update -u edcr-eddn-listen`.

## Verification

- Unit tests per slice; full suite within 0.0007 s per test.
- Live, after the user's go: the first timer run deploys the tip; a later push lands within about 10 minutes of its green `Tests` run; a deliberately broken listener commit is rejected and rolled back without touching the database.
