from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from edap.cargo_manifest import read_cargo_inventory


class CargoManifestTests(unittest.TestCase):
    def test_read_cargo_inventory_retries_when_status_reports_cargo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            cargo_path = journal_dir / "Cargo.json"
            cargo_path.write_text(json.dumps({"Inventory": []}), encoding="utf-8")
            (journal_dir / "Status.json").write_text(
                json.dumps({"Flags": 0, "Cargo": 461}),
                encoding="utf-8",
            )

            sleep_calls: list[float] = []

            def fake_sleep(delay_s: float) -> None:
                sleep_calls.append(delay_s)
                cargo_path.write_text(
                    json.dumps(
                        {
                            "Inventory": [
                                {"Name": "bertrandite", "Name_Localised": "Bertrandite", "Count": 461},
                            ]
                        }
                    ),
                    encoding="utf-8",
                )

            inventory = read_cargo_inventory(journal_dir, sleeper=fake_sleep)

        self.assertEqual(sleep_calls, [0.1])
        self.assertEqual(
            inventory,
            [{"Name": "bertrandite", "Name_Localised": "Bertrandite", "Count": 461}],
        )

    def test_read_cargo_inventory_does_not_retry_when_status_reports_empty_hold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            (journal_dir / "Cargo.json").write_text(json.dumps({"Inventory": []}), encoding="utf-8")
            (journal_dir / "Status.json").write_text(
                json.dumps({"Flags": 0, "Cargo": 0}),
                encoding="utf-8",
            )

            sleep_calls: list[float] = []
            inventory = read_cargo_inventory(journal_dir, sleeper=sleep_calls.append)

        self.assertEqual(inventory, [])
        self.assertEqual(sleep_calls, [])
