# Iteration Log

- Area: `haul`
- Title: `market-snapshot-publish-plan-0017-step-2`
- Started: `2026-11-15 11:08`

## Summary

- Plan 0017 step 2 built, code first: `tools/market_snapshot.py publish <db_path> [--work-dir] [--keep] [--dry-run]` writes the snapshot and `status.json` into a work dir, uploads the gzip, then `status.json`, then `manifest.json` last to an S3-compatible bucket, and prunes local snapshots to the newest `keep` (default 3). Remote pruning is left to an R2 lifecycle rule.
- Upload dependency: boto3 as the optional `publish` extra (`uv sync --extra publish`), imported lazily in `boto3_uploader` only. botocore is about 100 MB and VPS-only; rclone would be a separate binary; a hand-rolled SigV4 could not be verified against real R2 today. Without the extra, a real publish exits 1 naming the sync command. `write`, `--dry-run` and the default suite never import boto3 (its import alone exceeds the whole per-test budget).
- Settings come from `EDCR_SNAPSHOT_*` environment variables (endpoint, bucket, key id, secret; optional prefix, work dir, keep). systemd loads them with `EnvironmentFile=`; a shell run uses `uv run --env-file`. No env-file parser in the app.
- Cache headers: snapshot `application/gzip`, `public, max-age=31536000, immutable`; manifest and status `application/json`, `public, max-age=60`. Verified with the opt-in `EDCR_TEST_BOTO3=1` test against an in-process fake S3: boto3 sent exactly those headers.
- `status.json`: generated_at, newest_market_at, markets_updated_last_hour, disk_free_bytes, db_bytes; `messages_per_minute` is null with a note, since the listener's counters live in its own process.
- Deploy templates in `deploy/market-snapshot/` (listener service, oneshot publish service, hourly timer with jitter and `Persistent=true`, env example with placeholders) and the operator note `docs/operators/market-snapshot-vps.md` (checkout with uv, bucket, scoped token, lifecycle rule, dry run, first upload check with curl). Generic wording only; nothing deployed yet.

## Changes

- `edcr/market_publish.py`, `tests/test_market_publish.py`, `deploy/market-snapshot/*`, `docs/operators/market-snapshot-vps.md` (new); `tools/market_snapshot.py` (`publish` subcommand); `pyproject.toml` and `uv.lock` (optional extra); `docs/README.md`, plan 0017 (Status, Design > VPS, status.json fields, build step 2), `docs/status/haul.md`.
- Suite: 1213 tests (1 skipped without `EDCR_TEST_BOTO3`), 0.73 to 0.79 s on repeated runs against a 0.728 s budget. The timing report shows the slowest tests are pre-existing hub, control room and server tests (6 to 10 ms each); the two new files take 37 ms for 10 tests.

## Follow-ups

- Real deployment needs from the user: R2 endpoint URL, bucket name, access key id and secret (bucket-scoped Object Read & Write token), a public custom domain on the bucket, and the VPS itself (checkout path, uv path, service user, DB path, work dir, env file path replace the template placeholders).
- Step 3 (status Worker and Discord alarm), step 4 (client fetch and import with the 3 h refresh and the listener-on startup gap fetch), step 5 (player docs).
- The suite sits at the edge of the time budget; the next session that touches tests should look at the slowest hub and control room tests before adding more.
