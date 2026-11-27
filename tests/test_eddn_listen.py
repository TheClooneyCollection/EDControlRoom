from contextlib import chdir
from pathlib import Path
from tempfile import TemporaryDirectory
import tomllib
import unittest

from edcr.config import load_config
from tools.eddn_listen import main


class EddnListenTests(unittest.TestCase):
    def test_fresh_checkout_listens_with_defaults_without_creating_config(self) -> None:
        with TemporaryDirectory() as tmp, chdir(tmp):
            sessions = []
            self.assertEqual(main([], listen=lambda *settings: sessions.append(settings)), 0)
            self.assertEqual(sessions, [(Path('.eddn_markets.sqlite3'),
                                        'tcp://eddn.edcd.io:9500', 7 * 86400, 30.0)])
            self.assertFalse(Path('config.toml').exists())

    def test_command_line_overrides_defaults_with_or_without_local_config(self) -> None:
        with TemporaryDirectory() as tmp, chdir(tmp):
            database = Path(tmp) / 'collector.sqlite3'
            for local_config in (False, True):
                with self.subTest(local_config=local_config):
                    if local_config:
                        Path('config.toml').write_text(
                            '[eddn]\nrelay = "tcp://local:9500"\nmax_age_days = 2\n',
                            encoding='utf-8',
                        )
                    sessions = []
                    result = main(['--db', str(database), '--relay', 'tcp://override:9500',
                                   '--max-age-days', '3', '--status-every', '5'],
                                  listen=lambda *settings: sessions.append(settings))
                    self.assertEqual(result, 0)
                    self.assertEqual(sessions, [(database, 'tcp://override:9500', 3 * 86400, 5.0)])

    def test_existing_local_config_is_used(self) -> None:
        with TemporaryDirectory() as tmp, chdir(tmp):
            database = Path(tmp) / 'local.sqlite3'
            Path('config.toml').write_text(
                f"[eddn]\nrelay = 'tcp://local:9500'\ndatabase_file = '{database}'\nmax_age_days = 2\n",
                encoding='utf-8',
            )
            sessions = []
            self.assertEqual(main([], listen=lambda *settings: sessions.append(settings)), 0)
            self.assertEqual(sessions, [(database, 'tcp://local:9500', 2 * 86400, 30.0)])

    def test_invalid_local_config_is_reported_instead_of_using_defaults(self) -> None:
        with TemporaryDirectory() as tmp, chdir(tmp):
            Path('config.toml').write_text('[eddn', encoding='utf-8')
            with self.assertRaises(tomllib.TOMLDecodeError):
                main([], listen=lambda *settings: self.fail('Invalid config must stop startup'))

    def test_other_config_callers_still_require_their_config_file(self) -> None:
        with TemporaryDirectory() as tmp, chdir(tmp):
            for path in (Path('config.toml'), Path('explicit.toml')):
                with self.subTest(path=path), self.assertRaises(FileNotFoundError):
                    load_config(path)

    def test_check_reports_missing_current_and_future_versions_without_writes(self):
        from contextlib import closing, redirect_stdout
        import io
        import sqlite3
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'check.sqlite3'
            for version in (None, 0, 1, 2):
                with self.subTest(version=version):
                    if version is not None:
                        with closing(sqlite3.connect(path)) as db:
                            db.execute(f'PRAGMA user_version={version}')
                    before = path.read_bytes() if path.exists() else None
                    output = io.StringIO()
                    with redirect_stdout(output):
                        result = main(['--check', '--db', str(path)], listen=lambda *_: self.fail('Must not listen'))
                    self.assertEqual(result, int(version == 2))
                    self.assertEqual(output.getvalue(), f'schema db={version or 0} code=1\n')
                    self.assertEqual(path.read_bytes() if path.exists() else None, before)
                    self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), [] if version is None else ['check.sqlite3'])

    def test_check_import_failure_returns_failure(self):
        from contextlib import redirect_stderr
        import io
        from unittest.mock import patch
        with patch('tools.eddn_listen.importlib.import_module', side_effect=ImportError('broken import')), redirect_stderr(io.StringIO()) as output:
            self.assertEqual(main(['--check', '--db', 'unused.sqlite3']), 1)
        self.assertIn('broken import', output.getvalue())
