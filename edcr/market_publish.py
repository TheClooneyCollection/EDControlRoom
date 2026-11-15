"""Publish EDDN-only snapshots; the manifest is uploaded last as the release pointer."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path
import shutil
import sqlite3
from typing import Protocol

from edcr.market_snapshot import Manifest, write_snapshot


@dataclass(frozen=True)
class PublishSettings:
    endpoint_url: str
    bucket: str
    access_key_id: str = field(repr=False)
    secret_access_key: str = field(repr=False)
    prefix: str = ""
    work_dir: Path = Path("./snapshots")
    keep: int = 3

    @classmethod
    def from_env(cls, env: Mapping[str, str], *, dry_run: bool = False) -> PublishSettings:
        def required(name: str) -> str:
            value = env.get("EDCR_SNAPSHOT_" + name, "").strip()
            if not value:
                raise ValueError(f"Missing EDCR_SNAPSHOT_{name}")
            return value

        endpoint, bucket = required("ENDPOINT_URL"), required("BUCKET")
        access = env.get("EDCR_SNAPSHOT_ACCESS_KEY_ID", "") if dry_run else required("ACCESS_KEY_ID")
        secret = env.get("EDCR_SNAPSHOT_SECRET_ACCESS_KEY", "") if dry_run else required("SECRET_ACCESS_KEY")
        try:
            keep = int(env.get("EDCR_SNAPSHOT_KEEP", "3"))
        except ValueError:
            raise ValueError("EDCR_SNAPSHOT_KEEP must be a positive integer") from None
        if keep < 1:
            raise ValueError("EDCR_SNAPSHOT_KEEP must be a positive integer")
        return cls(endpoint, bucket, access, secret,
                   env.get("EDCR_SNAPSHOT_PREFIX", "").strip("/"),
                   Path(env.get("EDCR_SNAPSHOT_WORK_DIR", "./snapshots")), keep)


@dataclass(frozen=True)
class Upload:
    key: str
    path: Path
    content_type: str
    cache_control: str


@dataclass(frozen=True)
class PublishResult:
    manifest: Manifest
    status: dict[str, object]


class DiskUsage(Protocol):
    @property
    def free(self) -> int: ...


def publish(
    db_path: Path, work_dir: Path, settings: PublishSettings, *,
    upload: Callable[[Upload], None], now: Callable[[], datetime],
    disk_usage: Callable[[Path], DiskUsage] = shutil.disk_usage,
) -> PublishResult:
    if settings.keep < 1:
        raise ValueError("keep must be a positive integer")
    generated = now()
    manifest = write_snapshot(db_path, work_dir, now=lambda: generated)
    with closing(sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        recent = db.execute(
            "SELECT COUNT(*) FROM market WHERE updated_at >= ? AND updated_at <= ?",
            (generated.timestamp() - 3600, generated.timestamp()),
        ).fetchone()[0]
    status: dict[str, object] = {
        "generated_at": manifest["created_at"],
        "newest_market_at": manifest["newest_market_at"],
        "markets_updated_last_hour": recent,
        "messages_per_minute": None,
        "notes": ["messages_per_minute: the listener counts messages in its own process and does not persist them yet"],
        "disk_free_bytes": disk_usage(db_path.resolve().parent).free,
        "db_bytes": db_path.stat().st_size,
    }
    (work_dir / "status.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    for name, content_type, cache in (
        (manifest["file"], "application/gzip", "public, max-age=31536000, immutable"),
        ("status.json", "application/json", "public, max-age=60"),
        ("manifest.json", "application/json", "public, max-age=60"),
    ):
        key = f"{settings.prefix}/{name}" if settings.prefix else name
        upload(Upload(key, work_dir / name, content_type, cache))
    for old in sorted(work_dir.glob("markets-*.sqlite3.gz"), reverse=True)[settings.keep:]:
        old.unlink()
    return PublishResult(manifest, status)


def boto3_uploader(settings: PublishSettings) -> Callable[[Upload], None]:
    try:
        import boto3
    except ImportError:
        raise RuntimeError("Snapshot publishing needs boto3; run uv sync --extra publish") from None
    client = boto3.client(
        "s3", endpoint_url=settings.endpoint_url, aws_access_key_id=settings.access_key_id,
        aws_secret_access_key=settings.secret_access_key, region_name="auto",
    )

    def upload(item: Upload) -> None:
        client.upload_file(str(item.path), settings.bucket, item.key,
                           ExtraArgs={"ContentType": item.content_type, "CacheControl": item.cache_control})

    return upload
