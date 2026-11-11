from __future__ import annotations

import unittest

from edap.ship_range import fsd_max_fuel_per_jump, loadout_laden_jump_range

# A real Loadout (Panther Mk II, 7A SCO drive), cut to the fields the formula reads.
PANTHER = {"event": "Loadout", "Ship": "panthermkii", "UnladenMass": 1753.599976, "CargoCapacity": 1137,
           "MaxJumpRange": 29.390415, "FuelCapacity": {"Main": 128.0, "Reserve": 1.11},
           "Modules": [{"Slot": "FrameShiftDrive", "Item": "int_hyperdrive_overcharge_size7_class5"}]}


class LadenJumpRangeTests(unittest.TestCase):
    def test_a_real_loadout_matches_the_range_inara_searches_with(self) -> None:
        # 29.39 x (1753.6 + 12.8) / (1753.6 + 128 + 1137); plan 0014 measured 17.19, haul_search.toml had 17.2.
        self.assertEqual(loadout_laden_jump_range(PANTHER), 17.2)

    def test_fuel_per_jump_comes_from_the_drive_size_and_class(self) -> None:
        self.assertEqual(fsd_max_fuel_per_jump("int_hyperdrive_size5_class5"), 5.0)
        self.assertEqual(fsd_max_fuel_per_jump("Int_Hyperdrive_Size3_Class1"), 1.2)
        self.assertEqual(fsd_max_fuel_per_jump("int_hyperdrive_size8_class5"), 0.0)
        # An unknown drive counts no jump fuel, so the range reads a little short rather than long.
        unknown = {**PANTHER, "Modules": [{"Slot": "FrameShiftDrive", "Item": "int_hyperdrive_size9_class5"}]}
        self.assertEqual(loadout_laden_jump_range(unknown), 17.07)

    def test_a_loadout_missing_an_input_has_no_laden_range(self) -> None:
        for field in ("UnladenMass", "CargoCapacity", "MaxJumpRange", "FuelCapacity"):
            with self.subTest(field=field):
                self.assertIsNone(loadout_laden_jump_range({k: v for k, v in PANTHER.items() if k != field}))


if __name__ == "__main__":
    unittest.main()
