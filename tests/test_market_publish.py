from contextlib import closing, contextmanager, redirect_stderr, redirect_stdout
from dataclasses import replace
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from edcr.eddn.messages import CommodityPrice, MarketSnapshot
from edcr.eddn.store import EddnStore
from edcr.market_publish import PublishSettings, Upload, boto3_uploader, publish
from tools.market_snapshot import main

NOW = datetime(2026, 11, 15, 12, tzinfo=timezone.utc)
ENV = {"EDCR_SNAPSHOT_ENDPOINT_URL": "https://placeholder.invalid",
       "EDCR_SNAPSHOT_BUCKET": "test-bucket", "EDCR_SNAPSHOT_ACCESS_KEY_ID": "test-key",
       "EDCR_SNAPSHOT_SECRET_ACCESS_KEY": "test-secret"}


def create_store(path: Path) -> None:
    with closing(EddnStore.open(path)) as store:
        store.save([
            MarketSnapshot(index, "Sol", f"Station {index}", False, NOW.timestamp() - age,
                           (CommodityPrice("gold", 10, 20, 30, 40),), "")
            for index, age in enumerate((0, 3600, 3601, -1), 1)
        ])


@contextmanager
def environment(values):
    previous = dict(os.environ)
    try:
        os.environ.clear()
        os.environ.update(values)
        yield
    finally:
        os.environ.clear()
        os.environ.update(previous)


class MarketPublishTests(unittest.TestCase):
    def test_operator_publishes_snapshot_before_pointer_then_keeps_newest_local_files(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            database = root / "markets.sqlite3"
            create_store(database)
            work = root / "snapshots"
            work.mkdir()
            for name in ("markets-20261115T1000Z.sqlite3.gz", "markets-20261115T1100Z.sqlite3.gz"):
                (work / name).write_bytes(b"old")
            (work / "keep.txt").write_text("unrelated")
            settings = PublishSettings.from_env({**ENV, "EDCR_SNAPSHOT_PREFIX": "/data/", "EDCR_SNAPSHOT_KEEP": "2"})
            uploads = []
            result = publish(database, work, settings, upload=uploads.append, now=lambda: NOW,
                             disk_usage=lambda path: SimpleNamespace(free=1234))
            self.assertEqual([u.key for u in uploads], ["data/markets-20261115T1200Z.sqlite3.gz",
                                                      "data/status.json", "data/manifest.json"])
            self.assertEqual([(u.content_type, u.cache_control) for u in uploads], [
                ("application/gzip", "public, max-age=31536000, immutable"),
                ("application/json", "public, max-age=60"), ("application/json", "public, max-age=60")])
            self.assertEqual(result.status, {
                "generated_at": "2026-11-15T12:00:00Z", "newest_market_at": "2026-11-15T12:00:01Z",
                "markets_updated_last_hour": 2, "messages_per_minute": None,
                "notes": ["messages_per_minute: the listener counts messages in its own process and does not persist them yet"],
                "disk_free_bytes": 1234, "db_bytes": database.stat().st_size,
            })
            self.assertEqual(json.loads((work / "status.json").read_text()), result.status)
            self.assertEqual(json.loads((work / "manifest.json").read_text()), result.manifest)
            self.assertEqual(sorted(p.name for p in work.glob("*.gz")),
                             ["markets-20261115T1100Z.sqlite3.gz", "markets-20261115T1200Z.sqlite3.gz"])
            self.assertTrue((work / "keep.txt").exists())

    def test_failed_upload_never_publishes_pointer_or_prunes_local_snapshots(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            database = root / "markets.sqlite3"
            EddnStore.open(database).close()
            old = root / "markets-20261114T1200Z.sqlite3.gz"
            old.write_bytes(b"old")
            uploads = []

            def failing_upload(item):
                uploads.append(item.key)
                if item.key == "status.json":
                    raise OSError("offline")

            with self.assertRaisesRegex(OSError, "offline"):
                publish(database, root, replace(PublishSettings.from_env(ENV), keep=1),
                        upload=failing_upload, now=lambda: NOW,
                        disk_usage=lambda path: SimpleNamespace(free=0))
            self.assertEqual(uploads, ["markets-20261115T1200Z.sqlite3.gz", "status.json"])
            self.assertTrue(old.exists())
            status = json.loads((root / "status.json").read_text())
            self.assertEqual((status['newest_market_at'], status['markets_updated_last_hour']), (None, 0))

    def test_settings_name_missing_values_and_invalid_retention(self):
        for name in ENV:
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, name):
                PublishSettings.from_env({k: v for k, v in ENV.items() if k != name})
        for keep in ("0", "-1", "bad"):
            with self.subTest(keep=keep), self.assertRaisesRegex(ValueError, "EDCR_SNAPSHOT_KEEP"):
                PublishSettings.from_env({**ENV, "EDCR_SNAPSHOT_KEEP": keep})
        settings = PublishSettings.from_env(ENV)
        self.assertEqual((settings.prefix, settings.work_dir, settings.keep), ("", Path("snapshots"), 3))
        self.assertNotIn("test-secret", repr(settings))

    def test_cli_dry_run_needs_no_credentials_or_boto3_and_prints_uploads(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            database = root / "markets.sqlite3"
            create_store(database)
            stdout, stderr = io.StringIO(), io.StringIO()
            env = {k: v for k, v in ENV.items() if k.endswith(("URL", "BUCKET"))}
            with environment(env), redirect_stdout(stdout), redirect_stderr(stderr):
                result = main(["publish", str(database), "--work-dir", str(root / "out"), "--keep", "2", "--dry-run"])
            self.assertEqual(result, 0, stderr.getvalue())
            lines = stdout.getvalue().splitlines()
            self.assertEqual(len(lines), 4)
            self.assertTrue(lines[0].startswith("PUT s3://test-bucket/markets-"))
            self.assertIn("application/gzip  public, max-age=31536000, immutable", lines[0])
            self.assertTrue(lines[1].startswith("PUT s3://test-bucket/status.json"))
            self.assertTrue(lines[2].startswith("PUT s3://test-bucket/manifest.json"))
            self.assertEqual(json.loads(lines[3])["markets"], 4)
            self.assertNotIn("boto3", sys.modules)

    def test_cli_reports_configuration_error_in_one_line(self):
        stderr = io.StringIO()
        with environment({}), redirect_stderr(stderr):
            self.assertEqual(main(["publish", "unused.sqlite3"]), 1)
        self.assertEqual(stderr.getvalue(), "Snapshot failed: Missing EDCR_SNAPSHOT_ENDPOINT_URL\n")


@unittest.skipUnless(os.environ.get("EDCR_TEST_BOTO3") == "1", "opt-in local S3 integration")
class Boto3IntegrationTests(unittest.TestCase):
    def test_upload_reaches_local_s3_with_body_and_cache_headers(self):
        from http.server import BaseHTTPRequestHandler, HTTPServer
        from threading import Thread

        received = []

        class Handler(BaseHTTPRequestHandler):
            def do_PUT(self):
                body = self.rfile.read(int(self.headers["Content-Length"]))
                received.append((self.path, dict(self.headers), body))
                self.send_response(200)
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, *args):
                pass

        with HTTPServer(("127.0.0.1", 0), Handler) as server, TemporaryDirectory() as tmp:
            thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
            thread.start()
            try:
                settings = PublishSettings.from_env({**ENV, "EDCR_SNAPSHOT_ENDPOINT_URL":
                                                     f"http://127.0.0.1:{server.server_port}"})
                upload = boto3_uploader(settings)
                path = Path(tmp) / "object"
                path.write_bytes(b"snapshot content")
                for name, content_type, cache in (
                    ("data/snapshot.gz", "application/gzip", "public, max-age=31536000, immutable"),
                    ("data/manifest.json", "application/json", "public, max-age=60"),
                ):
                    upload(Upload(name, path, content_type, cache))
                    request_path, headers, body = received[-1]
                    self.assertEqual(request_path, "/test-bucket/" + name)
                    self.assertEqual(body, b"snapshot content")
                    self.assertEqual(headers["Content-Type"], content_type)
                    self.assertEqual(headers["Cache-Control"], cache)
                    print(f"S3 PUT {request_path}: Content-Type={headers['Content-Type']}; Cache-Control={headers['Cache-Control']}")
            finally:
                server.shutdown()
                thread.join()
