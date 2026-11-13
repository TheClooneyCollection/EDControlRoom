"""Count the journal events in the store, per node and event, without starting the Control Room."""
from __future__ import annotations

import argparse
from pathlib import Path
import sqlite3
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from edcr.config import load_config


def main(argv: list[str] | None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, help="Override hub.journal_events_file")
    parser.add_argument("--top", type=int, default=10, help="Events listed per node")
    args = parser.parse_args(argv)
    path = args.file or load_config().hub.journal_events_file
    if not path.exists():
        print(f"No journal event store at {path}", file=sys.stderr)
        return 1
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        nodes = db.execute(
            "SELECT node_id, COUNT(*), COUNT(DISTINCT file), datetime(MIN(timestamp), 'unixepoch'),"
            " datetime(MAX(timestamp), 'unixepoch') FROM journal_event GROUP BY node_id ORDER BY 2 DESC"
        ).fetchall()
        for node_id, count, files, first, last in nodes:
            print(f"{node_id}: {count:,} events in {files} files, {first} to {last} UTC")
            for event, n in db.execute(
                "SELECT event, COUNT(*) FROM journal_event WHERE node_id = ? GROUP BY event ORDER BY 2 DESC LIMIT ?",
                (node_id, args.top),
            ):
                print(f"  {n:>8,}  {event}")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
