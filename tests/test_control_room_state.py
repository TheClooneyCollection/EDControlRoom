from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from edap.control_room_state import (
    CommandHistoryEntry,
    ControlRoomState,
    load_control_room_state,
    save_control_room_state,
)
from edap.inara.trade_routes import TradeRoute


class ControlRoomStateTests(unittest.TestCase):
    def test_load_missing_file_returns_empty_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state = load_control_room_state(Path(temp_dir) / "missing.json")

        self.assertEqual(state.default_haul, {})
        self.assertEqual(state.history, [])
        self.assertFalse(state.instant_mode)
        self.assertEqual(state.session_profit, 0)
        self.assertEqual(state.session_elapsed_seconds, 0.0)

    def test_save_and_load_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "state.json"
            original = ControlRoomState(
                default_haul={"station_1_buying": "Aluminium", "station_2": "Hutton Orbital"},
                instant_mode=True,
                session_profit=12_345_678,
                session_elapsed_seconds=321.0,
                session_active=True,
                session_completed_runs=4,
                session_total_run_elapsed_seconds=600.0,
                session_last_run_profit=456_000,
                session_last_run_profit_delta=-44_000,
                session_last_run_elapsed_seconds=150.0,
                session_expected_profit_per_trip=500_000,
                session_expected_profit_per_trip_text="500,000 Cr",
                selected_trade_route=TradeRoute(
                    index=7,
                    from_station="Galileo",
                    from_system="Sol",
                    to_station="Irkutsk",
                    to_system="Alioth",
                    source_buy_commodity="Agronomic Treatment",
                    profit_per_hour="88.3m",
                ),
                running_trade_route=TradeRoute(
                    index=8,
                    from_station="Jameson Memorial",
                    from_system="Shinrarta Dezhra",
                    to_station="Abraham Lincoln",
                    to_system="Sol",
                    source_buy_commodity="Silver",
                ),
                history=[
                    CommandHistoryEntry(
                        raw="haul Aluminium",
                        command="haul",
                        params={"station_1_buying": "Aluminium", "dock_timeout": "600.0"},
                        timestamp="2026-06-07T12:00:00Z",
                    )
                ],
            )

            save_control_room_state(path, original)
            loaded = load_control_room_state(path)

        self.assertEqual(loaded.default_haul["station_1_buying"], "Aluminium")
        self.assertTrue(loaded.instant_mode)
        self.assertEqual(loaded.session_profit, 12_345_678)
        self.assertEqual(loaded.session_elapsed_seconds, 321.0)
        self.assertTrue(loaded.session_active)
        self.assertEqual(loaded.session_completed_runs, 4)
        self.assertEqual(loaded.session_total_run_elapsed_seconds, 600.0)
        self.assertEqual(loaded.session_last_run_profit, 456_000)
        self.assertEqual(loaded.session_last_run_profit_delta, -44_000)
        self.assertEqual(loaded.session_last_run_elapsed_seconds, 150.0)
        self.assertEqual(loaded.session_expected_profit_per_trip, 500_000)
        self.assertEqual(loaded.session_expected_profit_per_trip_text, "500,000 Cr")
        self.assertIsNotNone(loaded.selected_trade_route)
        self.assertEqual(loaded.selected_trade_route.to_system, "Alioth")
        self.assertEqual(loaded.selected_trade_route.profit_per_hour, "88.3m")
        self.assertIsNotNone(loaded.running_trade_route)
        self.assertEqual(loaded.running_trade_route.from_station, "Jameson Memorial")
        self.assertEqual(len(loaded.history), 1)
        self.assertEqual(loaded.history[0].raw, "haul Aluminium")
        self.assertEqual(loaded.history[0].params["dock_timeout"], "600.0")

    def test_loads_legacy_haul_defaults_key_for_backward_compatibility(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "state.json"
            path.write_text('{"haul_defaults":{"station_1_buying":"Gold"},"history":[]}', encoding="utf-8")

            loaded = load_control_room_state(path)

        self.assertEqual(loaded.default_haul["station_1_buying"], "Gold")
        self.assertFalse(loaded.instant_mode)


    def test_drops_legacy_one_way_haul_history_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "state.json"
            path.write_text(
                """
                {
                  "default_haul": {},
                  "history": [
                    {
                      "raw": "haul Aluminium",
                      "command": "haul",
                      "params": {
                        "commodity": "Aluminium",
                        "buy_station": "Trevithick Dock",
                        "sell_station": "Pawelczyk Dock",
                        "buy_system": "Achenar",
                        "sell_system": "Sol"
                      },
                      "timestamp": "2026-05-01T00:00:00Z"
                    },
                    {
                      "raw": "haul Bertrandite",
                      "command": "haul",
                      "params": {
                        "station_1_buying": "Aluminium",
                        "station_2_buying": "Bertrandite",
                        "station_1": "Pawelczyk Dock",
                        "station_2": "Trevithick Dock"
                      },
                      "timestamp": "2026-06-01T00:00:00Z"
                    },
                    {
                      "raw": "jump",
                      "command": "jump",
                      "params": {},
                      "timestamp": "2026-06-02T00:00:00Z"
                    }
                  ]
                }
                """,
                encoding="utf-8",
            )

            loaded = load_control_room_state(path)

        raws = [entry.raw for entry in loaded.history]
        self.assertEqual(raws, ["haul Bertrandite", "jump"])

    def test_drops_legacy_default_haul(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "state.json"
            path.write_text(
                '{"default_haul":{"commodity":"Aluminium","buy_station":"X","sell_station":"Y"},"history":[]}',
                encoding="utf-8",
            )

            loaded = load_control_room_state(path)

        self.assertEqual(loaded.default_haul, {})

    def test_drops_search_default_haul(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "state.json"
            path.write_text(
                '{"default_haul":{"mode":"search","near_system":"Sol","cargo_capacity":"460"},"history":[]}',
                encoding="utf-8",
            )

            loaded = load_control_room_state(path)

        self.assertEqual(loaded.default_haul, {})


if __name__ == "__main__":
    unittest.main()
