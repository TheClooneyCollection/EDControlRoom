"""Listen to the EDDN relay and keep the local market price database current."""
from __future__ import annotations

import argparse
from contextlib import closing
import importlib
import sqlite3
from pathlib import Path
import sys
import time
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from edcr.config import DEFAULT_CONFIG_PATH, DEFAULT_EDDN_CONFIG_PATH, load_config
from edcr.eddn.listener import EddnListener, open_zmq_socket
from edcr.eddn.service import status_line
from edcr.eddn.store import EddnStore


def run_listener(database: Path, relay: str, max_age_s: float, status_every: float) -> None:
    store = EddnStore.open(database)
    listener = EddnListener(
        store=store,
        open_socket=lambda: open_zmq_socket(relay),
        time_fn=time.time,
        max_age_s=max_age_s,
        log=print,
    )
    print(f"Listening to {relay}; Ctrl-C to stop.")
    listener.start()
    try:
        while True:
            time.sleep(status_every)
            print(status_line(listener.stats(), store.counts()), flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        listener.stop()
        try:
            listener.join(5.0)
        except KeyboardInterrupt:
            # A second Ctrl-C (uv forwards one too) only cuts the wait short.
            pass
        store.close()


def check_database(database: Path) -> int:
    """Report schema compatibility without initializing or migrating the database."""
    try:
        for module in ("edcr.eddn.listener", "edcr.eddn.store", "edcr.market_snapshot"):
            importlib.import_module(module)
        from edcr.eddn.store import SCHEMA_VERSION
        version = 0
        if database.exists():
            if database.with_name(database.name + "-wal").exists():
                with closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)) as db:
                    version = db.execute("PRAGMA user_version").fetchone()[0]
            else:
                # Opening a WAL-mode database can create sidecars even with mode=ro.
                with database.open("rb") as source:
                    header = source.read(100)
                if len(header) != 100 or header[:16] != b"SQLite format 3\x00":
                    raise ValueError("Invalid SQLite database header")
                version = int.from_bytes(header[60:64], "big")
        print(f"schema db={version} code={SCHEMA_VERSION}")
        return int(version > SCHEMA_VERSION)
    except Exception as error:
        print(f"Smoke check failed: {error}", file=sys.stderr)
        return 1


def main(
    argv: list[str] | None,
    *,
    listen: Callable[[Path, str, float, float], None] = run_listener,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check imports and database schema without writing")
    parser.add_argument("--db", type=Path, help="Override eddn.database_file")
    parser.add_argument("--relay", help="Override eddn.relay")
    parser.add_argument("--max-age-days", type=float, help="Override eddn.max_age_days")
    parser.add_argument("--status-every", type=float, default=30.0, help="Seconds between status lines")
    args = parser.parse_args(argv)
    if args.check:
        try:
            database = args.db
            if database is None:
                config_path = DEFAULT_CONFIG_PATH if DEFAULT_CONFIG_PATH.exists() else DEFAULT_EDDN_CONFIG_PATH
                database = load_config(config_path).eddn.database_file
            return check_database(database)
        except Exception as error:
            print(f"Smoke check failed: {error}", file=sys.stderr)
            return 1
    # Standalone collectors need only the shipped defaults, not a local config.
    config_path = DEFAULT_CONFIG_PATH if DEFAULT_CONFIG_PATH.exists() else DEFAULT_EDDN_CONFIG_PATH
    eddn = load_config(config_path).eddn
    listen(
        args.db or eddn.database_file,
        args.relay or eddn.relay,
        (args.max_age_days or eddn.max_age_days) * 86400,
        args.status_every,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
