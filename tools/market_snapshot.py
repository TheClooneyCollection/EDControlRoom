"""Write a local compressed market snapshot and manifest (no upload)."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys
from time import perf_counter

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from edcr.market_snapshot import write_snapshot


def main(argv: list[str] | None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    write = commands.add_parser("write", help="Write a snapshot from a database")
    write.add_argument("db_path", type=Path)
    write.add_argument("out_dir", type=Path)
    args = parser.parse_args(argv)
    started = perf_counter()
    try:
        manifest = write_snapshot(args.db_path, args.out_dir, now=lambda: datetime.now(timezone.utc))
    except (OSError, sqlite3.Error, ValueError) as error:
        print(f"Snapshot failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(manifest))
    print(f"{manifest['markets']} markets, {manifest['prices']} prices, "
          f"{manifest['bytes'] / 1_000_000:.2f} MB, {perf_counter() - started:.3f} seconds", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
