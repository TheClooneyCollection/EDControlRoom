"""Write, publish or fetch a compressed market snapshot and manifest."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from dataclasses import replace
from pathlib import Path
import sys
from time import perf_counter, time
from contextlib import closing
from urllib.request import urlopen

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from edcr.market_snapshot import fetch_and_import, write_snapshot
from edcr.eddn.store import EddnStore
from edcr.config import EddnConfig
from edcr.market_publish import PublishSettings, Upload, boto3_uploader, publish


def main(argv: list[str] | None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    write = commands.add_parser("write", help="Write a snapshot from a database")
    write.add_argument("db_path", type=Path)
    write.add_argument("out_dir", type=Path)
    publishing = commands.add_parser("publish", help="Publish to an S3-compatible bucket")
    publishing.add_argument("db_path", type=Path)
    publishing.add_argument("--work-dir", type=Path)
    publishing.add_argument("--keep", type=int)
    publishing.add_argument("--dry-run", action="store_true")
    fetching = commands.add_parser("fetch", help="Download and merge a market snapshot")
    fetching.add_argument("manifest_url")
    fetching.add_argument("db_path", type=Path)
    fetching.add_argument("--max-age-days", type=float, default=EddnConfig().max_age_days)
    args = parser.parse_args(argv)
    started = perf_counter()
    try:
        if args.command == "fetch":
            with closing(EddnStore.open(args.db_path)) as store:
                result = fetch_and_import(args.manifest_url, store, urlopen=urlopen, now=time,
                                          max_age_s=args.max_age_days * 86400, known_file=None)
            assert result is not None
            age = time() - datetime.fromisoformat(result.created_at.replace("Z", "+00:00")).timestamp()
            print(f"{result.file}: {result.bytes / 1_000_000:.2f} MB, snapshot age {age / 3600:.1f} h, "
                  f"imported {result.counts.markets} markets, {result.counts.prices} prices, "
                  f"{result.seconds:.3f} seconds")
            return 0
        if args.command == "write":
            manifest = write_snapshot(args.db_path, args.out_dir, now=lambda: datetime.now(timezone.utc))
        else:
            env = dict(os.environ)
            if args.keep is not None:
                env["EDCR_SNAPSHOT_KEEP"] = str(args.keep)
            settings = PublishSettings.from_env(env, dry_run=args.dry_run)
            if args.work_dir is not None:
                settings = replace(settings, work_dir=args.work_dir)

            def show_upload(item: Upload) -> None:
                print(f"PUT s3://{settings.bucket}/{item.key}  {item.path.stat().st_size} B  "
                      f"{item.content_type}  {item.cache_control}")

            uploader = show_upload if args.dry_run else boto3_uploader(settings)
            manifest = publish(args.db_path, settings.work_dir, settings, upload=uploader,
                               now=lambda: datetime.now(timezone.utc)).manifest
    except Exception as error:
        # CLI boundary includes optional SDK/network errors without importing botocore.
        print("Snapshot failed: " + " ".join(str(error).splitlines()), file=sys.stderr)
        return 1
    print(json.dumps(manifest))
    print(f"{manifest['markets']} markets, {manifest['prices']} prices, "
          f"{manifest['bytes'] / 1_000_000:.2f} MB, {perf_counter() - started:.3f} seconds", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
