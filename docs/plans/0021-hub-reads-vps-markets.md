# 0021: Hub Reads the VPS Market Snapshot

## Status

Decisions confirmed 2026-11-19; nothing built.

## Why

A VPS already runs `tools/eddn_listen.py` around the clock on its own EDDN-only DB. The hub's own listener misses everything while the hub Mac sleeps or is off, so after time offline `/routes` and Best deal rank on a DB with gaps. The hub should fill them from the VPS DB.

[Plan 0017](0017-hosted-market-snapshot.md) built the pieces: `tools/market_snapshot.py write` (`VACUUM INTO`, gzip, manifest written last) and the client `[eddn] snapshot_url`, which fetches a manifest, checks sha256 and merges. This plan wires them together privately, without R2.

## Decisions (confirmed with the user)

- Private: the data is for ourselves only. No R2, no public URL, no Cloudflare.
- Transport over Tailscale. Anything on the VPS is reachable only from localhost and the tailnet, never other interfaces.
- Serve with `tailscale serve` pointed at a snapshot directory on its own HTTPS port. tailscaled serves it on the tailnet address only; no host port opens and no nginx site is added. The ufw rule allowing all traffic on `tailscale0` already exists, so no firewall change is needed.
- The hub keeps its own EDDN listener on and fills gaps at start only (the plan 0017 `startup_only` mode): it fetches once when its DB is empty or its newest market is over 1 h old. No periodic refresh while the listener runs.
- Merge rule unchanged: per market, the newest `updated_at` wins and a newer market replaces the whole station (`EddnStore.import_database`). The hub's own `Market.json` markets and peer pushes are newer than the VPS copy when fresher, so they stay. Re-importing a snapshot changes nothing.
- Cadence: the VPS writes a snapshot hourly (VACUUM about 7 s, about 36 MB gzip), so a hub start sees data at most about an hour old plus the listener catching up from there.

## Rejected (with reasons)

- nginx on `127.0.0.1` behind a `tailscale serve` proxy: one more service and config for the same result; cache headers do not matter for one private client.
- Hub pulls with ssh/rsync: needs a key on the Mac and a new local import path; the HTTP fetch already exists and is tested.
- Reading the VPS DB live over the network: SQLite over a network filesystem is unsafe with a live WAL writer.
- Periodic refresh with the hub listener on: needs a code change; gaps only appear while the hub is down, and start-up fills them.

## Design

Fixed interfaces between the two repos:

- Snapshot dir on the VPS: `/var/lib/edcontrolroom/snapshots`, written by the `edcontrolroom` user, mode 0755, files 0644.
- Command: `uv run --no-sync python3 tools/market_snapshot.py write <db_path> <snapshot_dir> --keep 3`, run from the checkout.
- Served files: `manifest.json` and `markets-<UTC minute>.sqlite3.gz` at the root of the served URL. The manifest is replaced last, so it only ever names a complete file; `--keep 3` keeps the file a hub is mid-download on.
- Hub config (on the hub, not in either repo): `[eddn] snapshot_url = "https://<vps tailnet name>:<port>/manifest.json"`, `enabled = true`.

### EDCR part (this repo)

1. `tools/market_snapshot.py write` gains optional `--keep N` (positive int). After the manifest is written, delete all but the newest N `markets-*.sqlite3.gz` in `out_dir`. Omitted means no pruning, as today. Move the prune loop from `publish` (`edcr/market_publish.py`) into one shared helper used by both.
2. Tests: `write --keep` prunes older files, leaves the manifest's file, rejects `--keep 0`; `publish` keeps passing unchanged.
3. Docs: a short "Private snapshot over Tailscale" section in [the VPS operator guide](../operators/market-snapshot-vps.md): the write timer, `tailscale serve --https=<port> <snapshot_dir>`, hub `snapshot_url`, and that the hub fetches only at start while its listener runs. No host names, IPs or tailnet names. Status line in `docs/status/haul.md`.

### Lighthouse part (`ansible-project-lighthouse`)

1. Role `edcr_eddn_listener`: create the snapshot dir; add `edcr-market-snapshot.service` (oneshot, `edcontrolroom` user, the write command above) and `edcr-market-snapshot.timer` (`OnCalendar=hourly`, `Persistent=true`, `RandomizedDelaySec=120`). Variables for dir, keep and schedule in defaults.
2. A second `tailscale_serve` instance (for example `tailscale-serve-edcr-markets`) with `tailscale_serve_backend_url` set to the snapshot dir and its own `tailscale_serve_https_port` (not 443, which Umami uses). The port and tailnet name stay in lighthouse vars.
3. Do not reboot the VPS; `systemctl daemon-reload` and starting the new units are enough.

## Build steps

1. EDCR: `write --keep`, tests, operator doc section. Merge to `main`; the VPS checkout tracks `main`.
2. Lighthouse: the timer, the dir and the serve instance; apply, then run the snapshot service once by hand.
3. Hub: set `snapshot_url`, restart the hub with a DB whose newest market is over 1 h old (or run the fetch below), and check the log line and the Routes panel source and age.

## Validation

- On the VPS: `curl -fsS https://<vps tailnet name>:<port>/manifest.json` works from another tailnet device and fails on the public address; `ss -tlnp` shows no new listener on a public interface.
- After a few hours the snapshot dir holds 3 gzip files and the manifest names the newest.
- On the hub: `uv run python3 tools/market_snapshot.py fetch <manifest_url> <copy of the hub DB>` imports and prints counts. This also proves the hub's Python trusts the `ts.net` certificate; if it does not, fall back to `tailscale serve --http=<port>` (traffic is already WireGuard-encrypted) and say so in the doc.
- A hub start after time offline logs `Market snapshot: ...` and fresher local markets stay untouched (covered by the existing import tests).
