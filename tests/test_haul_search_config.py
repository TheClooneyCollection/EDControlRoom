from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from edap.haul_search_config import HaulSearchConfigError, load_haul_search_config


class HaulSearchConfigTests(unittest.TestCase):
    def test_load_haul_search_config_reads_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "haul_search.toml"
            config_path.write_text(
                """
[haul_search]
max_route_distance_ly = "70"
max_price_age_hours = "6"
cargo_capacity = 512
min_landing_pad = "medium"
max_station_distance_ls = "700"
use_surface_stations = "yes_with_odyssey"
min_supply = "4000"
min_demand = "3000"
include_round_trips = false
order_by = "distance"
""".strip(),
                encoding="utf-8",
            )

            loaded = load_haul_search_config(config_path)

        self.assertEqual(loaded["cargo_capacity"], "512")
        self.assertEqual(loaded["min_landing_pad"], "medium")
        self.assertEqual(loaded["include_round_trips"], "false")
        self.assertEqual(loaded["order_by"], "distance")

    def test_load_haul_search_config_rejects_non_integer_capacity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "haul_search.toml"
            config_path.write_text(
                """
[haul_search]
cargo_capacity = "460"
""".strip(),
                encoding="utf-8",
            )

            with self.assertRaises(HaulSearchConfigError):
                load_haul_search_config(config_path)


if __name__ == "__main__":
    unittest.main()
