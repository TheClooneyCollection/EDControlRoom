from contextlib import closing, redirect_stdout, redirect_stderr
import gzip
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import io
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest.mock import patch
from urllib.request import ProxyHandler, build_opener

from edcr.eddn.messages import CarrierName, CarrierSighting, CommodityPrice, MarketSnapshot, StationInfo, SystemPosition
from edcr.eddn.store import EddnStore, SCHEMA_VERSION
from edcr.market_snapshot import download_snapshot, fetch_and_import
from tools.market_snapshot import main
from tests.test_eddn import memory_store


URL = 'https://snapshots.example/data/manifest.json'
# Loopback requests must not consult the operators system proxy settings.
urlopen = build_opener(ProxyHandler({})).open
TABLES = ('system', 'station', 'market', 'price', 'carrier_access', 'carrier_name', 'carrier_seen', 'carrier_scan')


def market(key=1, timestamp=1000, names=('gold', 'silver'), access=''):
    return MarketSnapshot(key, 'Sol', f'Station {key}', False, timestamp,
                          tuple(CommodityPrice(name, 10, 20, 30, 40) for name in names), access)


def rows(db):
    return {table: db.execute(f'SELECT * FROM {table} ORDER BY 1, 2').fetchall() for table in TABLES}


def packed(updates):
    with closing(memory_store()) as store:
        store.save(updates)
        return store._db.serialize()


class SnapshotFetchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database = packed([market()])
        cls.compressed = gzip.compress(cls.database)
        cls.manifest = dict(file='markets-test.sqlite3.gz', created_at='1970-01-01T00:20:00Z',
                            newest_market_at='1970-01-01T00:16:40Z', markets=1, prices=2,
                            bytes=len(cls.compressed), sha256=hashlib.sha256(cls.compressed).hexdigest(),
                            schema=SCHEMA_VERSION)

    def fetch(self, store, *, manifest=None, compressed=None, known_file=None):
        metadata = self.manifest if manifest is None else manifest
        payload = self.compressed if compressed is None else compressed
        requested = []

        def open_url(url):
            requested.append(url)
            if url == URL:
                return io.BytesIO(json.dumps(metadata).encode())
            self.assertEqual(url, 'https://snapshots.example/data/markets-test.sqlite3.gz')
            return io.BytesIO(payload)

        result = fetch_and_import(URL, store, urlopen=open_url, now=lambda: 1200,
                                  max_age_s=500, known_file=known_file)
        return result, requested

    def test_empty_install_gets_prices_and_keeps_newer_local_prices_on_refresh(self):
        with closing(memory_store()) as store:
            db = store._db
            result, _ = self.fetch(store)
            self.assertEqual((result.counts.markets, result.counts.prices), (1, 2))
            store.save([market(timestamp=1100, names=('platinum',))])
            result, _ = self.fetch(store)
            self.assertEqual((result.counts.markets, result.counts.prices), (0, 0))
            self.assertEqual(db.execute('SELECT commodity FROM price').fetchall(), [('platinum',)])

    def test_older_snapshot_is_migrated_before_exact_version_import(self):
        with patch('edcr.eddn.store.SCHEMA_VERSION', 2), patch('edcr.market_snapshot.SCHEMA_VERSION', 2), patch(
            'edcr.eddn.store.MIGRATIONS', {1: lambda db: db.execute('CREATE TABLE upgraded (value)')}
        ), closing(memory_store()) as store:
            result, _ = self.fetch(store)
            self.assertEqual(result.counts.markets, 1)
            self.assertEqual(store.counts().prices, 2)

    def test_known_file_checks_only_the_manifest(self):
        with closing(memory_store()) as store:
            result, requested = self.fetch(store, known_file=self.manifest['file'])
            self.assertIsNone(result)
            self.assertEqual(requested, [URL])

    def test_schema_mismatch_is_refused_before_downloading(self):
        requested = []

        def open_url(url):
            requested.append(url)
            return io.BytesIO(json.dumps(dict(self.manifest, schema=999)).encode())

        with closing(memory_store()) as store:
            with self.assertRaisesRegex(ValueError, 'update the hub'):
                fetch_and_import(URL, store, urlopen=open_url, now=lambda: 1200, max_age_s=500, known_file=None)
            self.assertEqual(requested, [URL])
            self.assertEqual(store.counts().markets, 0)

    def test_bad_hash_leaves_local_database_unchanged(self):
        with closing(memory_store()) as store:
            db = store._db
            store.save([market(timestamp=900)])
            before, counts = rows(db), store.counts()
            with self.assertRaisesRegex(ValueError, 'sha256'):
                self.fetch(store, manifest=dict(self.manifest, sha256='0' * 64))
            self.assertEqual(rows(db), before)
            self.assertEqual(store.counts(), counts)

    def test_invalid_or_truncated_downloads_and_hash_failures_remove_temporary_files(self):
        with TemporaryDirectory() as tmp:
            dest = Path(tmp)
            for data, manifest in ((b'not gzip', self.manifest), (self.compressed[:-5], self.manifest),
                                   (self.compressed, dict(self.manifest, sha256='0' * 64)),
                                   (self.compressed, dict(self.manifest, bytes=1))):
                with self.subTest(length=len(data), manifest=manifest), self.assertRaises((OSError, EOFError, ValueError)):
                    download_snapshot(manifest, URL, dest, urlopen=lambda url: io.BytesIO(data))
                self.assertEqual(list(dest.iterdir()), [])

    def test_http_failure_preserves_database_and_removes_download_file(self):
        def offline(url):
            raise OSError('offline')

        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(OSError, 'offline'):
                download_snapshot(self.manifest, URL, Path(tmp), urlopen=offline)
            self.assertEqual(list(Path(tmp).iterdir()), [])
        with closing(memory_store()) as store:
            db = store._db
            store.save([market()])
            before = rows(db)
            with self.assertRaises(OSError):
                fetch_and_import(URL, store, urlopen=offline, now=lambda: 1200, max_age_s=500, known_file=None)
            self.assertEqual(rows(db), before)

    def test_real_http_stream_populates_an_empty_install(self):
        manifest, compressed = self.manifest, self.compressed

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                body = json.dumps(manifest).encode() if self.path.endswith('manifest.json') else compressed
                self.send_response(200)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        with HTTPServer(('127.0.0.1', 0), Handler) as server:
            server.timeout = 2

            def serve_requests():
                for _ in range(4):
                    server.handle_request()

            worker = Thread(target=serve_requests, daemon=True)
            worker.start()
            try:
                with closing(memory_store()) as store:
                    result = fetch_and_import(f'http://127.0.0.1:{server.server_port}/manifest.json', store,
                                              urlopen=urlopen, now=lambda: 1200, max_age_s=500, known_file=None)
                    self.assertEqual(result.counts.prices, 2)
                    self.assertEqual(store.counts().markets, 1)
                with TemporaryDirectory() as tmp, redirect_stdout(io.StringIO()) as output, \
                        patch('tools.market_snapshot.urlopen', new=urlopen):
                    self.assertEqual(main(['fetch', f'http://127.0.0.1:{server.server_port}/manifest.json',
                                           str(Path(tmp) / 'cli.sqlite3'), '--max-age-days', '999999']), 0)
                    self.assertIn('imported 1 markets, 2 prices', output.getvalue())
                    self.assertIn('snapshot age', output.getvalue())
            finally:
                worker.join(timeout=5)
            self.assertFalse(worker.is_alive())

    def test_import_matches_saving_updates_for_every_table(self):
        initial = [market(1, 2000), market(2, 800), market(4, 800),
                   SystemPosition(1, 'old', 1, 2, 3, 1000), SystemPosition(2, 'keep', 1, 2, 3, 2000),
                   SystemPosition(3, 'equal', 1, 2, 3, 1000),
                   StationInfo(1, 1, 'Sol', 'Station 1', 'Outpost', 42, 'L', 1000),
                   StationInfo(2, 1, 'Sol', 'Station 2', 'Outpost', 42, 'L', 2000),
                   StationInfo(3, 1, 'Sol', 'Station 3', 'Outpost', 42, 'L', 1000),
                   CarrierName('ABC-123', 'old', 1000), CarrierName('DEF-456', 'same', 1000),
                   CarrierName('OLD-123', 'keep', 2000),
                   CarrierSighting('ABC-123', 1, 1000, False), CarrierSighting('DEF-456', 1, 1000, False),
                   CarrierSighting('GHI-789', 1, 1000, False), CarrierSighting('JKL-123', 1, 1000, True),
                   CarrierSighting('OLD-123', 1, 2000, False), CarrierSighting('EQL-123', 1, 1100, False),
                   CarrierSighting('REF-123', 1, 100, False)]
        updates = [market(1, 1100, access='all'), market(2, 1100, ('gold',)), market(3, 1100), market(4, 600),
                   SystemPosition(1, 'new', 4, 5, 6, 1100), SystemPosition(2, 'older', 4, 5, 6, 1100),
                   SystemPosition(3, 'equal-new', 4, 5, 6, 1000), SystemPosition(4, 'fresh', 4, 5, 6, 1100),
                   StationInfo(1, 1, 'Sol', 'ABC-123', 'Outpost', None, '', 1100),
                   StationInfo(2, 1, 'Sol', 'Station 2', 'Outpost', None, '', 1100),
                   StationInfo(3, 1, 'Sol', 'Station 3', 'FleetCarrier', None, '', 1000),
                   StationInfo(5, 1, 'Sol', 'Station 5', 'Outpost', None, '', 1100),
                   CarrierName('ABC-123', 'new', 1100), CarrierName('DEF-456', 'same', 1100),
                   CarrierName('OLD-123', 'older', 1100), CarrierName('NEW-123', 'fresh', 1100),
                   CarrierSighting('ABC-123', 2, 1100, False), CarrierSighting('DEF-456', 1, 1100, False),
                   CarrierSighting('GHI-789', 1, 1101, True), CarrierSighting('JKL-123', 1, 900, True),
                   CarrierSighting('OLD-123', 2, 1100, False), CarrierSighting('EQL-123', 2, 1100, False),
                   CarrierSighting('REF-123', 1, 1100, False)]
        with TemporaryDirectory() as tmp, closing(sqlite3.connect(':memory:')) as actual, closing(sqlite3.connect(':memory:')) as expected:
            source = Path(tmp) / 'snapshot.sqlite3'
            # Import equivalence needs the stored rows; snapshot publication has its own tests.
            source.write_bytes(packed(updates))
            imported, saved = EddnStore(actual, backup=lambda start, target: None), EddnStore(expected, backup=lambda start, target: None)
            imported.save(initial)
            saved.save(initial)
            saved.save([item for item in updates if not isinstance(item, MarketSnapshot) or item.timestamp >= 700])
            counts = imported.import_database(source, min_updated_at=700)
            self.assertEqual(rows(actual), rows(expected))
            self.assertEqual((counts.markets, counts.prices, counts.stations, counts.systems), (2, 3, 3, 3))
            repeated = imported.import_database(source, min_updated_at=700)
            self.assertEqual((repeated.markets, repeated.prices), (0, 0))
            self.assertEqual(rows(actual), rows(expected))

    def test_broken_database_rolls_back_import_but_preserves_pending_local_updates(self):
        with TemporaryDirectory() as tmp, closing(sqlite3.connect(':memory:')) as db:
            source = Path(tmp) / 'snapshot.sqlite3'
            source.write_bytes(self.database)
            store = EddnStore(db, backup=lambda start, target: None)
            store.apply(market(5))
            before = rows(db)
            with closing(sqlite3.connect(source)) as broken:
                broken.execute('DROP TABLE carrier_seen')
                broken.commit()
            with self.assertRaises(sqlite3.Error):
                store.import_database(source, min_updated_at=0)
            self.assertEqual(rows(db), before)
            # A second successful import proves both rollback cleanup and DETACH occurred.
            source.write_bytes(self.database)
            store.import_database(source, min_updated_at=0)
            self.assertEqual(store.counts().markets, 2)

    def test_copied_database_schema_is_checked_even_with_valid_manifest(self):
        with TemporaryDirectory() as tmp, closing(sqlite3.connect(':memory:')) as db:
            path = Path(tmp) / 'new.sqlite3'
            path.write_bytes(self.database)
            with closing(sqlite3.connect(path)) as source:
                source.execute('PRAGMA user_version=999')
            data = gzip.compress(path.read_bytes())
            manifest = dict(self.manifest, bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
            store = EddnStore(db, backup=lambda start, target: None)
            with self.assertRaisesRegex(ValueError, 'Unsupported market schema'):
                self.fetch(store, compressed=data, manifest=manifest)
            self.assertEqual(store.counts().markets, 0)

    def test_cli_reports_one_line_on_download_failure(self):
        with TemporaryDirectory() as tmp, redirect_stderr(io.StringIO()) as error, \
                patch('tools.market_snapshot.urlopen', new=urlopen):
            self.assertEqual(main(['fetch', 'invalid-url', str(Path(tmp) / 'cli.sqlite3')]), 1)
            self.assertEqual(len(error.getvalue().splitlines()), 1)
            self.assertIn('Snapshot failed:', error.getvalue())
