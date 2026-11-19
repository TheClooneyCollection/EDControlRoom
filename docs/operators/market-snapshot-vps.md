# Publish market snapshots from a VPS

`tools/market_snapshot.py publish` writes a gzip snapshot, `status.json` and
`manifest.json`, then uploads them to an S3-compatible bucket in that order.
The manifest is the last upload, so it only points to a completed snapshot.
The tool copies every table verbatim: publish only the dedicated EDDN-only VPS
database, never a hub database containing a pilot's markets or journal sightings.
The status Worker and Discord alarm are a later step, not installed here.

## Prepare the checkout

Install `uv` and clone the checkout on a VPS. Create a dedicated `edcontrolroom`
system user and group, and give it access to the checkout and a writable state
directory. All paths in `deploy/market-snapshot/` are installation placeholders:
`/opt/edcontrolroom` for the checkout, `/usr/local/bin/uv` for uv,
`/var/lib/edcontrolroom` for the DB and snapshots, and
`/etc/edcontrolroom/market-publish.env` for credentials. Adjust them together.

As the service user, from the checkout:

```sh
uv sync --extra publish
```

boto3 is an optional publisher dependency; ordinary clients, `write` and dry runs
do not need or import it. The units use `uv run --no-sync` against the environment
prepared above so the listener and publisher do not change it concurrently.
Repeat `uv sync --extra publish` after updating the checkout while the services
are stopped. The publishing adapter uses region `auto` and client-default addressing.

## Private snapshot over Tailscale

For private hub gap filling, serve a snapshot directory over Tailscale. From the
checkout, a oneshot service running as `edcontrolroom` writes the dedicated
EDDN-only database snapshot:

```sh
uv run --no-sync python3 tools/market_snapshot.py write <db_path> <snapshot_dir> --keep 3
```

Use a write timer with `OnCalendar=hourly`, `Persistent=true` and
`RandomizedDelaySec=120`. Give the service user a writable snapshot directory;
keep the directory readable (0755) and its files readable (0644) by tailscaled.
The manifest is replaced after the gzip is complete; only then are older gzip
files pruned. `--keep` requires a positive integer; omitting it keeps every file.
Run one writer per directory, with at least a minute between writes, and retain
three snapshots to allow downloads of the preceding manifest to finish.

Serve the directory using a dedicated HTTPS port:

```sh
tailscale serve --https=<port> <snapshot_dir>
```

Keep this Serve configuration running persistently through the deployment's
service manager. Serve makes it available within the tailnet; do not enable
Funnel or a public web listener. Set the hub's local configuration to:

```toml
[eddn]
enabled = true
snapshot_url = "<served HTTPS base URL>/manifest.json"
```

With its EDDN listener enabled, the hub fetches only at startup when its database
is empty or its newest market is over one hour old. There is no periodic snapshot
refresh while that listener runs. A merge replaces a station only when the
snapshot's market is newer, preserving fresher hub and peer data. Check the
startup `Market snapshot: ...` log and the Routes source/age display after
configuring the URL and restarting the hub. The write timer and Serve service
are deployment configuration; this section does not install them.

## Set up the bucket by hand

1. Create the bucket in R2 and attach the custom domain for public reads.
2. Create an R2 API token with **Object Read & Write**, scoped only to the bucket.
   Save the S3 endpoint URL, Access Key ID and Secret Access Key in the environment
   file copied from `deploy/market-snapshot/market-publish.env.example`.
   Restrict access to that file; never commit credentials.
   See [R2 authentication](https://developers.cloudflare.com/r2/api/tokens/).
3. In the dashboard, add an object lifecycle deletion rule after about 7 days.
   Filter by the literal prefix `markets-` at the bucket root, or
   `<prefix>/markets-` when `EDCR_SNAPSHOT_PREFIX` is set. R2 filters by prefix,
   not a wildcard suffix: this keeps `manifest.json` and `status.json` outside
   the rule. Reserve that prefix for snapshots. The tool does not delete remote
   objects. See [R2 object lifecycles](https://developers.cloudflare.com/r2/buckets/object-lifecycles/).

Required environment values are `EDCR_SNAPSHOT_ENDPOINT_URL`,
`EDCR_SNAPSHOT_BUCKET`, `EDCR_SNAPSHOT_ACCESS_KEY_ID` and
`EDCR_SNAPSHOT_SECRET_ACCESS_KEY`. Optional values are `EDCR_SNAPSHOT_PREFIX`
(empty by default), `EDCR_SNAPSHOT_WORK_DIR` (`./snapshots` by default), and
`EDCR_SNAPSHOT_KEEP` (3 by default, positive integer). `--work-dir` and `--keep`
override the environment. Supply the DB path as the positional argument.

## Verify locally, then upload

Start the listener on its own database. It is the only writer: do not run another
listener or a hub against that path. A dry run needs only endpoint and bucket
(placeholders work); it creates the real snapshot and status locally, prints each
would-be PUT and the manifest JSON, and applies local retention without a network call.

```sh
uv run --env-file /etc/edcontrolroom/market-publish.env python3 tools/market_snapshot.py publish /var/lib/edcontrolroom/markets.sqlite3 --dry-run
uv run --extra publish --env-file /etc/edcontrolroom/market-publish.env python3 tools/market_snapshot.py publish /var/lib/edcontrolroom/markets.sqlite3
```

`uv run --env-file` is supported by the verified uv installation. systemd loads
the same file with `EnvironmentFile=`; there is no application env-file parser.
Real runs print manifest JSON to stdout and counts, MB and seconds to stderr.
Errors exit 1 with one line. A failed upload stops before later objects and before
local pruning. After success, only the newest `keep` timestamped local gzip files
remain. Run only one publisher per work directory and bucket prefix, and avoid
rerunning within the same UTC minute: snapshot names have minute resolution and
are served with immutable caching.

Set `SNAPSHOT_BASE_URL` in your shell to the custom domain URL including any key
prefix, without a trailing slash, and `SNAPSHOT_FILE` to the printed manifest's
`file` value. Verify public access:

```sh
curl -fsS "$SNAPSHOT_BASE_URL/manifest.json"
curl -fsSI "$SNAPSHOT_BASE_URL/manifest.json"
curl -fsSI "$SNAPSHOT_BASE_URL/status.json"
curl -fsSI "$SNAPSHOT_BASE_URL/$SNAPSHOT_FILE"
```

The remote `file` must match the published manifest. JSON responses should carry
`Content-Type: application/json` and `Cache-Control: public, max-age=60`; the gzip
should carry `application/gzip` and `public, max-age=31536000, immutable`.
Ensure any CDN cache rules respect those headers, including caching JSON, and do
not impose a long TTL on the manifest. A local S3 stand-in checks the adapter's
PUT body and these headers with:

```sh
EDCR_TEST_BOTO3=1 uv run --extra publish python3 -m unittest tests.test_market_publish.Boto3IntegrationTests
```

`status.json` reports market freshness, markets updated in the last hour, free
disk space and the main DB file size (WAL size is not included). The count is a
read-only source query just after the snapshot, so a live update can make it
slightly newer than the manifest. `messages_per_minute` is null with a note:
the listener's process-local message counters are not persisted.

## Enable the services

Copy the three adjusted units from `deploy/market-snapshot/` into
`/etc/systemd/system/`, install the environment file, then run:

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now edcr-eddn-listen.service
sudo systemctl start edcr-market-publish.service
sudo systemctl enable --now edcr-market-publish.timer
systemctl list-timers edcr-market-publish.timer
journalctl -u edcr-eddn-listen.service -u edcr-market-publish.service
```

Let the listener initialize the database before the first publish. The publisher
runs hourly with up to two minutes of jitter, catches missed timer runs after
boot, and retains three local snapshots by default. systemd will not overlap the
same oneshot service; manual commands must also respect the single-publisher rule.
These are deployment templates; the local test does not validate a real bucket,
CDN, VPS or systemd installation.
