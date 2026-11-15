"""Background startup gap filling and periodic hosted market snapshots."""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
import threading
from typing import Any

from edcr.eddn.store import EddnStore, SnapshotImport
from edcr.market_snapshot import UrlOpen, fetch_and_import


class _Stopped(Exception):
    pass


class SnapshotRefresh:
    """Own the worker and synchronize shutdown with database access."""

    def __init__(self, store: EddnStore, stop: threading.Event, status: dict[str, Any]):
        self._store = store
        self._stop = stop
        self._status = status
        self._lock = threading.Lock()
        self._database_lock = threading.Lock()
        self._thread: threading.Thread | None = None

    def status(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._status)

    def _update(self, **values: Any) -> None:
        with self._lock:
            self._status.update(values)

    def import_database(self, path: Path, *, min_updated_at: float) -> SnapshotImport:
        # Downloads can finish after shutdown. Never let them use a closed store.
        with self._database_lock:
            if self._stop.is_set():
                raise _Stopped()
            return self._store.import_database(path, min_updated_at=min_updated_at)

    def stop(self) -> None:
        self._stop.set()
        # An import already in progress must finish before the owner closes SQLite.
        with self._database_lock:
            pass
        if self._thread is not None:
            self._thread.join(timeout=0.2)
        self._update(next_check_at=None)


def start_snapshot_refresh(
    store: EddnStore, *, manifest_url: str, refresh_s: float, listener_on: bool,
    max_age_s: float, urlopen: UrlOpen, now: Callable[[], float], log: Callable[[str], None],
    stop: threading.Event,
) -> SnapshotRefresh:
    mode = "off" if not manifest_url else "startup_only" if listener_on else "timer"
    refresh = SnapshotRefresh(store, stop, {
        "url": manifest_url, "mode": mode, "last_check_at": None, "last_fetch_at": None,
        "file": None, "snapshot_created_at": None, "newest_market_at": None,
        "markets_imported": 0, "prices_imported": 0, "next_check_at": None, "error": None,
    })

    def check() -> None:
        refresh._update(last_check_at=now())
        try:
            result = fetch_and_import(
                manifest_url, refresh, urlopen=urlopen, now=now, max_age_s=max_age_s,
                known_file=refresh.status()["file"],
            )
            if stop.is_set():
                return
            refresh._update(error=None)
            if result is None:
                return
            fetched_at = now()
            refresh._update(
                last_fetch_at=fetched_at, file=result.file, snapshot_created_at=result.created_at,
                newest_market_at=result.newest_market_at, markets_imported=result.counts.markets,
                prices_imported=result.counts.prices,
            )
            age = ("unknown" if result.newest_market_at is None else
                   f"{max(0, fetched_at - datetime.fromisoformat(result.newest_market_at.replace('Z', '+00:00')).timestamp()) / 3600:.1f} h")
            log(f"Market snapshot: {result.file}, {result.bytes / 1_000_000:.1f} MB, data {age} old, "
                f"{result.counts.markets} markets and {result.counts.prices} prices imported in {result.seconds:.1f} s")
        except _Stopped:
            return
        except Exception as exc:
            if not stop.is_set():
                message = " ".join(str(exc).splitlines())
                refresh._update(error=message)
                log(f"Warning: Market snapshot: {message}")

    def run() -> None:
        try:
            with refresh._database_lock:
                if stop.is_set():
                    return
                counts = store.counts()
            if not counts.markets or counts.newest_market_at is None or now() - counts.newest_market_at > 3600:
                check()
            if listener_on:
                return
            while not stop.is_set():
                refresh._update(next_check_at=now() + refresh_s)
                if stop.wait(refresh_s):
                    break
                check()
        except Exception as exc:
            if not stop.is_set():
                message = " ".join(str(exc).splitlines())
                refresh._update(error=message)
                log(f"Warning: Market snapshot: {message}")
        finally:
            refresh._update(next_check_at=None)

    if manifest_url:
        refresh._thread = threading.Thread(target=run, name="market-snapshot", daemon=True)
        refresh._thread.start()
    return refresh
