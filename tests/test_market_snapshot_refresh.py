from contextlib import closing
import gzip
import hashlib
import io
import json
import sqlite3
import threading
from types import SimpleNamespace
import unittest

from edcr.eddn.store import EddnStore, SnapshotImport, SCHEMA_VERSION
from edcr.market_snapshot_refresh import start_snapshot_refresh


class ControlledStop:
    def __init__(self, steps=()):
        self.steps = iter(steps)
        self.stopped = False
        self.finished = threading.Event()
        self.waits = []

    def is_set(self):
        return self.stopped

    def set(self):
        self.stopped = True

    def wait(self, seconds):
        self.waits.append(seconds)
        step = next(self.steps, None)
        if step is None:
            self.set()
            self.finished.set()
            return True
        step()
        return False


class RecordingStore:
    def __init__(self, newest=None):
        self.newest = newest
        self.imported = []
        self.read = threading.Event()

    def counts(self):
        self.read.set()
        return SimpleNamespace(markets=int(self.newest is not None), newest_market_at=self.newest)

    def import_database(self, path, *, min_updated_at):
        self.imported.append((path.read_bytes(), min_updated_at))
        return SnapshotImport(markets=2, prices=3, stations=0, systems=0, carriers=0)


class SnapshotRefreshTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with closing(sqlite3.connect(":memory:")) as connection:
            EddnStore(connection, backup=lambda start, target: None)
            cls.database = connection.serialize()
        cls.payload = gzip.compress(cls.database)

    def start(self, *, listener=False, newest=None, steps=(), fail=False, stop_download=False, url="https://example.invalid/manifest.json"):
        self.clock = 10000.0
        self.filename = "first.sqlite3.gz"
        self.requests = []
        self.logs = []
        self.logged = threading.Event()
        self.store = RecordingStore(newest)
        self.stop = ControlledStop(steps)
        self.fail = fail

        def open_url(url):
            self.requests.append(url)
            if self.fail:
                raise OSError("offline\nretry later")
            if url.endswith("manifest.json"):
                return io.BytesIO(json.dumps(dict(
                    file=self.filename, created_at="1970-01-01T02:00:00Z",
                    newest_market_at="1970-01-01T02:00:00Z", markets=2, prices=3,
                    bytes=len(self.payload), sha256=hashlib.sha256(self.payload).hexdigest(),
                    schema=SCHEMA_VERSION,
                )).encode())
            if stop_download:
                self.stop.set()
                self.stop.finished.set()
            return io.BytesIO(self.payload)

        def log(line):
            self.logs.append(line)
            self.logged.set()

        refresh = start_snapshot_refresh(
            self.store, manifest_url=url, refresh_s=30, listener_on=listener,
            max_age_s=1000, urlopen=open_url, now=lambda: self.clock, log=log, stop=self.stop,
        )
        self.addCleanup(refresh.stop)
        return refresh

    def test_listener_fills_startup_gap_without_timer(self):
        refresh = self.start(listener=True)
        self.assertTrue(self.logged.wait(2))
        refresh.stop()
        self.assertEqual(self.stop.waits, [])
        status = refresh.status()
        self.assertEqual((status["mode"], status["next_check_at"]), ("startup_only", None))
        self.assertEqual((status["markets_imported"], status["prices_imported"]), (2, 3))
        self.assertEqual(len(self.store.imported), 1)
        self.assertIn("2 markets and 3 prices imported", self.logs[0])

    def test_recent_listener_store_and_disabled_url_do_not_download(self):
        for url, newest in (("https://example.invalid/manifest.json", 9999), ("", None)):
            refresh = self.start(listener=True, newest=newest, url=url)
            if url:
                self.assertTrue(self.store.read.wait(2))
            refresh.stop()
            self.assertEqual(self.requests, [])
            self.assertEqual(self.logs, [])

    def test_timer_skips_same_file_then_imports_changed_file(self):
        def unchanged():
            self.clock += 30
        def changed():
            self.clock += 30
            self.filename = "second.sqlite3.gz"
        refresh = self.start(steps=(unchanged, changed))
        self.assertTrue(self.stop.finished.wait(2))
        refresh.stop()
        self.assertEqual(len(self.store.imported), 2)
        self.assertEqual(len(self.logs), 2)
        self.assertEqual(sum(url.endswith("manifest.json") for url in self.requests), 3)
        self.assertEqual(refresh.status()["file"], "second.sqlite3.gz")
        self.assertEqual(refresh.status()["last_fetch_at"], 10060)

    def test_offline_timer_reports_warning_and_recovers_next_interval(self):
        def recover():
            self.fail = False
            self.clock += 30
        refresh = self.start(fail=True, steps=(recover,))
        self.assertTrue(self.stop.finished.wait(2))
        refresh.stop()
        self.assertIn("Warning: Market snapshot: offline retry later", self.logs)
        self.assertIsNone(refresh.status()["error"])
        self.assertEqual(len(self.store.imported), 1)

    def test_shutdown_during_download_never_imports_into_the_closed_store(self):
        refresh = self.start(listener=True, stop_download=True)
        self.assertTrue(self.stop.finished.wait(2))
        refresh.stop()
        self.assertEqual(self.store.imported, [])
        self.assertEqual(self.logs, [])
        self.assertIsNone(refresh.status()["last_fetch_at"])
