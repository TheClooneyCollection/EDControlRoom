from contextlib import closing, redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
import gzip
import hashlib
import io
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from edcr.eddn.messages import CarrierSighting, CommodityPrice, MarketSnapshot
from edcr.eddn.store import EddnStore, SCHEMA_VERSION
from edcr.market_snapshot import write_snapshot
from tools.market_snapshot import main

NOW = datetime(2026, 11, 15, 13, 30, tzinfo=timezone(timedelta(hours=2)))


class MarketSnapshotTests(unittest.TestCase):
    def test_operator_snapshots_a_live_store_and_gets_a_matching_manifest(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            database = root / "market #1.sqlite3"
            with closing(EddnStore.open(database)) as store:
                store.save([
                    MarketSnapshot(i, "Sol", f"Station {i}", False, NOW.timestamp() - i,
                                   (CommodityPrice("gold", 10, 20, 30, 40),), "")
                    for i in (1, 2)
                ] + [CarrierSighting("ABC-123", 1, NOW.timestamp(), True)])
                manifest = write_snapshot(database, root / "out", now=lambda: NOW)
                self.assertEqual(manifest['file'], 'markets-20261115T1130Z.sqlite3.gz')
                artifact = root / "out" / manifest['file']
                data = artifact.read_bytes()
                restored = root / "restored.sqlite3"
                restored.write_bytes(gzip.decompress(data))
                with closing(sqlite3.connect(restored)) as db:
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM market").fetchone()[0], 2)
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM price").fetchone()[0], 2)
                    self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], SCHEMA_VERSION)
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM carrier_scan").fetchone()[0], 1)
                self.assertEqual(manifest, {
                    "file": artifact.name, "created_at": "2026-11-15T11:30:00Z",
                    "newest_market_at": "2026-11-15T11:29:59Z", "markets": 2, "prices": 2,
                    "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "schema": SCHEMA_VERSION,
                })
                self.assertEqual(json.loads((root / "out" / "manifest.json").read_text()), manifest)
                self.assertEqual(sorted(p.name for p in (root / "out").iterdir()),
                                 sorted([artifact.name, "manifest.json"]))

    def test_empty_store_and_cli_write_produce_a_manifest(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            database = root / "markets.sqlite3"
            EddnStore.open(database).close()
            manifest = write_snapshot(database, root / "out", now=lambda: NOW)
            self.assertEqual((manifest['markets'], manifest['prices'], manifest['newest_market_at']), (0, 0, None))
            stdout, stderr = io.StringIO(), io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                result = main(["write", str(database), str(root / "cli")])
            self.assertEqual(result, 0)
            self.assertEqual(json.loads(stdout.getvalue()), json.loads((root / "cli" / "manifest.json").read_text()))
            self.assertIn("0 markets, 0 prices,", stderr.getvalue())

    def test_cli_write_retains_requested_snapshots_and_unrelated_files(self) -> None:
        for keep in (None, 1, 2, 5):
            with self.subTest(keep=keep), TemporaryDirectory() as tmp:
                root = Path(tmp)
                database = root / "markets.sqlite3"
                EddnStore.open(database).close()
                out = root / "out"
                out.mkdir()
                old_names = [f"markets-20000101T0{hour}00Z.sqlite3.gz" for hour in range(3)]
                for name in old_names:
                    (out / name).write_bytes(b"old")
                (out / "notes.txt").write_text("keep me", encoding="utf-8")
                args = ["write", str(database), str(out)]
                if keep is not None:
                    args.extend(["--keep", str(keep)])
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    self.assertEqual(main(args), 0)
                manifest = json.loads((out / "manifest.json").read_text())
                expected = sorted(old_names + [manifest["file"]])
                if keep is not None:
                    expected = expected[-keep:]
                self.assertEqual(sorted(p.name for p in out.glob("markets-*.sqlite3.gz")), expected)
                artifact = (out / manifest["file"]).read_bytes()
                self.assertEqual(hashlib.sha256(artifact).hexdigest(), manifest["sha256"])
                self.assertEqual((out / "notes.txt").read_text(), "keep me")

    def test_cli_write_rejects_invalid_retention_before_writing(self) -> None:
        for keep in ("0", "-1", "bad", "1.5"):
            with self.subTest(keep=keep), TemporaryDirectory() as tmp:
                out = Path(tmp) / "out"
                stderr = io.StringIO()
                with redirect_stderr(stderr), self.assertRaises(SystemExit) as error:
                    main(["write", str(Path(tmp) / "missing.sqlite3"), str(out), "--keep", keep])
                self.assertEqual(error.exception.code, 2)
                self.assertIn("must be a positive integer", stderr.getvalue())
                self.assertFalse(out.exists())

    def test_failed_write_keeps_existing_manifest_and_snapshots(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / "markets-20000101T0000Z.sqlite3.gz"
            old.write_bytes(b"old")
            pointer = root / "manifest.json"
            pointer.write_text(json.dumps({"file": old.name}), encoding="utf-8")
            with redirect_stderr(io.StringIO()):
                result = main(["write", str(root / "missing.sqlite3"), str(root), "--keep", "1"])
            self.assertEqual(result, 1)
            self.assertEqual(old.read_bytes(), b"old")
            self.assertEqual(json.loads(pointer.read_text()), {"file": old.name})

    def test_incompatible_database_is_refused_without_publishing(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            database = root / "markets.sqlite3"
            EddnStore.open(database).close()
            with closing(sqlite3.connect(database)) as db:
                db.execute(f"PRAGMA user_version = {SCHEMA_VERSION + 1}")
            # Opening a future database must not relabel it as the current schema.
            EddnStore.open(database).close()
            with self.assertRaisesRegex(ValueError, "Unsupported market schema"):
                write_snapshot(database, root / "out", now=lambda: NOW)
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                self.assertEqual(main(["write", str(database), str(root / "out")]), 1)
            self.assertIn("Unsupported market schema", stderr.getvalue())
            self.assertEqual(list((root / "out").iterdir()), [])

    def test_legacy_unstamped_store_is_copied_without_changing_source(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            database = root / "markets.sqlite3"
            EddnStore.open(database).close()
            with closing(sqlite3.connect(database)) as db:
                db.execute("PRAGMA user_version = 0")
            manifest = write_snapshot(database, root / "out", now=lambda: NOW)
            self.assertEqual(manifest['schema'], SCHEMA_VERSION)
            with closing(sqlite3.connect(database)) as db:
                self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 0)
            copy = root / "copy.sqlite3"
            copy.write_bytes(gzip.decompress((root / "out" / manifest['file']).read_bytes()))
            with closing(sqlite3.connect(copy)) as db:
                self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], SCHEMA_VERSION)
            EddnStore.open(database).close()
            with closing(sqlite3.connect(database)) as db:
                self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], SCHEMA_VERSION)
