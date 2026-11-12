from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from edcr.config import load_config
from edcr.eddn.messages import SystemPosition
from edcr.market_db import open_market_store, station_facts_writer

SOL = SystemPosition(address=10, name="Sol", x=0.0, y=0.0, z=0.0, timestamp=1.0)


class MarketDbTests(unittest.TestCase):
    def test_hub_and_standalone_open_the_store_without_eddn_and_a_peer_never_does(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            database = Path(tmp) / "db" / "markets.sqlite3"
            for role, opens in (("standalone", True), ("hub", True), ("peer", False)):
                path.write_text(f"[eddn]\nenabled = false\ndatabase_file = '{database}'\n[hub]\nrole = \"{role}\"\ntoken = \"t\"\n",
                                encoding="utf-8")
                store = open_market_store(load_config(path))
                self.assertEqual(store is not None, opens, role)
                if store is not None:
                    station_facts_writer(store, self.fail)([SOL])
                    self.assertEqual(store.counts().systems, 1)
                    store.close()

    def test_a_peer_keeps_no_facts_and_a_store_error_is_logged_not_raised(self) -> None:
        logs: list[str] = []
        station_facts_writer(None, logs.append)([SOL])
        self.assertEqual(logs, [])

        class BrokenStore:
            def save(self, updates: list) -> None:
                raise sqlite3.OperationalError("database is locked")

        station_facts_writer(BrokenStore(), logs.append)([SOL])  # type: ignore[arg-type]
        self.assertEqual(logs, ["Warning: failed to record station facts: database is locked"])


if __name__ == "__main__":
    unittest.main()
