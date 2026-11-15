"""Write a verbatim market database snapshot, including every stored table.

Publish only from the VPS database holding EDDN data only, never a hub database:
privacy comes from the source database, not from stripping records here.
"""
from __future__ import annotations

from collections.abc import Callable
from contextlib import closing
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
from tempfile import TemporaryDirectory
from typing import TypedDict

from edcr.eddn.store import SCHEMA_VERSION


class Manifest(TypedDict):
    file: str
    created_at: str
    newest_market_at: str | None
    markets: int
    prices: int
    bytes: int
    sha256: str
    schema: int


def _utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def write_snapshot(db_path: Path, out_dir: Path, *, now: Callable[[], datetime]) -> Manifest:
    """Copy a live WAL database read-only and describe the resulting frozen copy."""
    created = now()
    if created.utcoffset() is None:
        raise ValueError("Snapshot time must include a timezone")
    filename = f"markets-{created.astimezone(timezone.utc):%Y%m%dT%H%MZ}.sqlite3.gz"
    out_dir.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".market-snapshot-", dir=out_dir) as tmp:
        frozen = Path(tmp) / "markets.sqlite3"
        with closing(sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True)) as source:
            version = source.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, SCHEMA_VERSION):
                raise ValueError(f"Unsupported market schema {version}; expected {SCHEMA_VERSION}")
            source.execute("VACUUM INTO ?", (str(frozen),))
        with closing(sqlite3.connect(frozen.resolve().as_uri() + "?mode=ro", uri=True)) as snapshot:
            markets, newest = snapshot.execute("SELECT COUNT(*), MAX(updated_at) FROM market").fetchone()
            prices = snapshot.execute("SELECT COUNT(*) FROM price").fetchone()[0]
        compressed = Path(tmp) / filename
        with frozen.open("rb") as input_file, gzip.open(compressed, "wb", compresslevel=9) as output:
            shutil.copyfileobj(input_file, output)
        with compressed.open("rb") as output:
            digest = hashlib.file_digest(output, "sha256").hexdigest()
        manifest = Manifest(
            file=filename, created_at=_utc(created),
            newest_market_at=None if newest is None else _utc(datetime.fromtimestamp(newest, timezone.utc)),
            markets=markets, prices=prices, bytes=compressed.stat().st_size,
            sha256=digest, schema=SCHEMA_VERSION,
        )
        staged_manifest = Path(tmp) / "manifest.json"
        staged_manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        compressed.replace(out_dir / filename)
        staged_manifest.replace(out_dir / "manifest.json")
    return manifest
