from contextlib import closing
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from edcr.eddn.store import EddnStore, migrate


class StoreMigrationTests(unittest.TestCase):
    def test_fresh_and_unversioned_stores_open_without_backup(self):
        for legacy in (False, True):
            with self.subTest(legacy=legacy), closing(sqlite3.connect(':memory:')) as db:
                if legacy:
                    db.execute('CREATE TABLE legacy (value)')
                store = EddnStore(db, backup=lambda *_: self.fail('No migration needed'))
                self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 1)
                self.assertEqual(store.counts().markets, 0)

    def test_steps_preserve_data_and_backup_contains_original_shape(self):
        with closing(sqlite3.connect(':memory:')) as db:
            db.executescript('CREATE TABLE data (value); INSERT INTO data VALUES (7); PRAGMA user_version=1;')
            backups = []
            migrate(db, target=3, migrations={
                1: lambda db: db.execute('ALTER TABLE data ADD COLUMN extra'),
                2: lambda db: db.execute('UPDATE data SET extra=value+1'),
            }, backup=lambda start, end: backups.append((start, end, db.serialize())))
            self.assertEqual(db.execute('SELECT * FROM data').fetchall(), [(7, 8)])
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 3)
            self.assertEqual([(a, b) for a, b, _ in backups], [(1, 3)])
            with closing(sqlite3.connect(':memory:')) as original:
                original.deserialize(backups[0][2])
                self.assertEqual(original.execute('SELECT * FROM data').fetchall(), [(7,)])

    def test_failed_step_rolls_back_ddl_and_keeps_last_completed_version(self):
        with closing(sqlite3.connect(':memory:')) as db:
            db.execute('PRAGMA user_version=1')
            def fail(db):
                db.execute('ALTER TABLE data ADD COLUMN lost')
                raise RuntimeError('broken step')
            with self.assertRaisesRegex(RuntimeError, 'broken step'):
                migrate(db, target=3, migrations={1: lambda db: db.execute('CREATE TABLE data (value)'), 2: fail},
                        backup=lambda *_: None)
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 2)
            self.assertEqual([row[1] for row in db.execute('PRAGMA table_info(data)')], ['value'])

    def test_newer_database_and_missing_ladder_fail_before_backup(self):
        with closing(sqlite3.connect(':memory:')) as db:
            db.execute('PRAGMA user_version=2')
            with self.assertRaisesRegex(ValueError, 'newer than this code'):
                EddnStore(db, backup=lambda *_: self.fail('Must not back up'))
            with self.assertRaisesRegex(ValueError, 'Missing market schema migration'):
                migrate(db, target=3, migrations={}, backup=lambda *_: self.fail('Must not back up'))

    def test_backup_failure_leaves_database_at_original_version(self):
        with closing(sqlite3.connect(':memory:')) as db:
            db.execute('PRAGMA user_version=1')
            def fail(*_):
                raise OSError('disk full')
            with self.assertRaisesRegex(OSError, 'disk full'):
                migrate(db, target=2, migrations={1: lambda db: db.execute('CREATE TABLE data (value)')}, backup=fail)
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT name FROM sqlite_master').fetchall(), [])

    def test_open_keeps_one_backup_with_pre_migration_data(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'market.sqlite3'
            with closing(EddnStore.open(path)):
                pass
            old = Path(str(path) + '.pre-v1')
            old.write_bytes(b'old backup')
            with patch('edcr.eddn.store.SCHEMA_VERSION', 2), patch('edcr.eddn.store.MIGRATIONS', {1: lambda db: db.execute('CREATE TABLE added (value)')}):
                with closing(EddnStore.open(path)):
                    pass
            self.assertFalse(old.exists())
            with closing(sqlite3.connect(str(path) + '.pre-v2')) as backup:
                self.assertEqual(backup.execute('PRAGMA user_version').fetchone()[0], 1)
                self.assertIsNone(backup.execute("SELECT name FROM sqlite_master WHERE name='added'").fetchone())

    def test_retry_after_partial_upgrade_preserves_original_backup(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'market.sqlite3'
            with closing(EddnStore.open(path)):
                pass
            def fail(db):
                raise RuntimeError('second step fails')
            with patch('edcr.eddn.store.SCHEMA_VERSION', 3), patch('edcr.eddn.store.MIGRATIONS', {
                1: lambda db: db.execute('CREATE TABLE added (value)'), 2: fail,
            }):
                with self.assertRaisesRegex(RuntimeError, 'second step fails'):
                    EddnStore.open(path)
            backup_path = Path(str(path) + '.pre-v3')
            original = backup_path.read_bytes()
            with closing(sqlite3.connect(path)) as db:
                self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 2)
            with patch('edcr.eddn.store.SCHEMA_VERSION', 3), patch('edcr.eddn.store.MIGRATIONS', {
                2: lambda db: db.execute('INSERT INTO added VALUES (42)'),
            }), closing(EddnStore.open(path)) as store:
                self.assertEqual(store._db.execute('PRAGMA user_version').fetchone()[0], 3)
            self.assertEqual(backup_path.read_bytes(), original)
            with closing(sqlite3.connect(backup_path)) as db:
                self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 1)
