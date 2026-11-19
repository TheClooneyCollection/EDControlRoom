"""Write a verbatim market database snapshot, including every stored table.

Publish only from the VPS database holding EDDN data only, never a hub database:
privacy comes from the source database, not from stripping records here.
"""
from __future__ import annotations

from collections.abc import Callable
from contextlib import closing
from datetime import datetime, timezone
from dataclasses import dataclass
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
from tempfile import TemporaryDirectory, NamedTemporaryFile
from time import perf_counter
from urllib.parse import urljoin
from typing import ContextManager, Protocol, TypedDict, cast

from edcr.eddn.store import SCHEMA_VERSION, SnapshotImport


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
        with closing(sqlite3.connect(frozen)) as snapshot:
            # A store created before SCHEMA_VERSION existed is still 0; the copy always carries the version.
            snapshot.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
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


def prune_snapshots(out_dir: Path, keep: int) -> None:
    """Keep the newest timestamped artifacts after their manifest is published."""
    if keep < 1:
        raise ValueError("keep must be a positive integer")
    for old in sorted(out_dir.glob("markets-*.sqlite3.gz"), reverse=True)[keep:]:
        old.unlink()


class DownloadStream(Protocol):
    def read(self, size: int = -1) -> bytes: ...


UrlOpen = Callable[[str], ContextManager[DownloadStream]]


@dataclass(frozen=True)
class FetchResult:
    file: str
    created_at: str
    newest_market_at: str | None
    bytes: int
    counts: SnapshotImport
    seconds: float


def read_manifest(url: str, *, urlopen: UrlOpen) -> Manifest:
    """Reject incompatible or malformed metadata before requesting its artifact."""
    with urlopen(url) as response:
        value = json.loads(response.read())
    if not isinstance(value, dict):
        raise ValueError("Snapshot manifest must be an object")
    if type(value.get("schema")) is not int or value["schema"] != SCHEMA_VERSION:
        raise ValueError(f"Unsupported market schema {value.get('schema')}; expected {SCHEMA_VERSION}")
    for key in ("markets", "prices", "bytes"):
        if type(value.get(key)) is not int or value[key] < 0:
            raise ValueError(f"Invalid manifest {key}")
    if not isinstance(value.get("file"), str) or not value["file"]:
        raise ValueError("Invalid manifest file")
    digest = value.get("sha256")
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdefABCDEF" for c in digest):
        raise ValueError("Invalid manifest sha256")
    for key in ("created_at", "newest_market_at"):
        timestamp = value.get(key)
        if key == "newest_market_at" and key in value and timestamp is None:
            continue
        if not isinstance(timestamp, str) or datetime.fromisoformat(timestamp.replace("Z", "+00:00")).utcoffset() is None:
            raise ValueError(f"Invalid manifest {key}")
    return cast(Manifest, value)


def download_snapshot(manifest: Manifest, base_url: str, dest_dir: Path, *, urlopen: UrlOpen) -> Path:
    """Hash the compressed stream while decompressing; return only a verified file."""
    digest = hashlib.sha256()
    size = 0

    class HashingReader:
        def __init__(self, stream: DownloadStream) -> None:
            self.stream = stream

        def read(self, count: int = -1) -> bytes:
            nonlocal size
            data = self.stream.read(count)
            digest.update(data)
            size += len(data)
            return data

    dest_dir.mkdir(parents=True, exist_ok=True)
    temporary = NamedTemporaryFile(prefix=".market-import-", suffix=".sqlite3", dir=dest_dir, delete=False)
    path = Path(temporary.name)
    try:
        with temporary as output:
            with urlopen(urljoin(base_url, manifest["file"])) as response:
                with gzip.GzipFile(fileobj=HashingReader(response), mode="rb") as source:
                    shutil.copyfileobj(source, output, length=1024 * 1024)
            if digest.hexdigest() != manifest["sha256"].lower():
                raise ValueError("Snapshot sha256 mismatch")
            if size != manifest["bytes"]:
                raise ValueError("Snapshot byte count mismatch")
    except BaseException:
        # The context closes first, including on flush errors, for Windows unlink.
        path.unlink(missing_ok=True)
        raise
    return path


class SnapshotStore(Protocol):
    def import_database(self, path: Path, *, min_updated_at: float) -> SnapshotImport: ...


def fetch_and_import(
    manifest_url: str, store: SnapshotStore, *, urlopen: UrlOpen, now: Callable[[], float],
    max_age_s: float, known_file: str | None,
) -> FetchResult | None:
    started = perf_counter()
    manifest = read_manifest(manifest_url, urlopen=urlopen)
    if manifest["file"] == known_file:
        return None
    with TemporaryDirectory(prefix="market-import-") as tmp:
        path = download_snapshot(manifest, manifest_url, Path(tmp), urlopen=urlopen)
        counts = store.import_database(path, min_updated_at=now() - max_age_s)
    return FetchResult(manifest["file"], manifest["created_at"], manifest["newest_market_at"],
                       manifest["bytes"], counts, perf_counter() - started)
