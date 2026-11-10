from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from edap.haul_config import HaulConfigError, load_haul_config


class HaulConfigTests(unittest.TestCase):
    def test_load_haul_config_reads_nested_toml_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "haul.toml"
            config_path.write_text(
                """
[haul]
galaxy_map_settle = 4.5
dock_timeout = 900.0

[haul.station_1]
buying = "Aluminium"
name = "Pawelczyk Dock"
system = "Sol"
manual_landing = false

[haul.station_2]
buying = "Bertrandite"
name = "Trevithick Dock"
system = "Achenar"
manual_landing = true
""".strip(),
                encoding="utf-8",
            )

            loaded = load_haul_config(config_path)

        self.assertEqual(loaded["station_1_buying"], "Aluminium")
        self.assertEqual(loaded["station_1"], "Pawelczyk Dock")
        self.assertEqual(loaded["station_1_system"], "Sol")
        self.assertEqual(loaded["station_1_manual_landing"], "false")
        self.assertEqual(loaded["station_2_buying"], "Bertrandite")
        self.assertEqual(loaded["station_2"], "Trevithick Dock")
        self.assertEqual(loaded["station_2_system"], "Achenar")
        self.assertEqual(loaded["station_2_manual_landing"], "true")
        self.assertEqual(loaded["galaxy_map_settle"], "4.5")
        self.assertEqual(loaded["dock_timeout"], "900.0")

    def test_load_haul_config_still_reads_the_old_on_land_keys(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "haul.toml"
            config_path.write_text("[haul]\nstation_1_on_land = true\n\n[haul.station_2]\non_land = true\n", encoding="utf-8")

            loaded = load_haul_config(config_path)

        self.assertEqual((loaded["station_1_manual_landing"], loaded["station_2_manual_landing"]), ("true", "true"))

    def test_load_haul_config_rejects_non_boolean_manual_landing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "haul.toml"
            config_path.write_text(
                """
[haul.station_1]
manual_landing = "no"
""".strip(),
                encoding="utf-8",
            )

            with self.assertRaises(HaulConfigError):
                load_haul_config(config_path)

