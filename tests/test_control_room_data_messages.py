from __future__ import annotations

from types import SimpleNamespace
import unittest

from edap.control_room.dependencies import LocalControlRoomDataSource
from edap.control_room.models import HaulStats, MarketData, RuntimeUIState, ShipState
from edap.control_room.protocol.data_messages import (
    CONTROL_ROOM_HYDRATE,
    DATA_MESSAGE_SCHEMA,
    DATA_MESSAGE_VERSION,
    data_read_model_from_message,
    hydrate_message,
    is_control_room_data_message,
)
from edap.control_room.protocol.events import ActivityLogEntry
from edap.control_room_state import ControlRoomState


class ControlRoomDataMessagesTests(unittest.TestCase):
    def test_hydrate_message_wraps_data_source_read_model(self) -> None:
        app = SimpleNamespace(
            _ship=ShipState(system="Sol"),
            _market=MarketData(station="Galileo", market_id=3229359104),
            _haul_stats=HaulStats(
                station_1="Galileo",
                completed_runs=3,
                cargo_moved_t=156,
                session_started_at=50.0,
                active=True,
                current_run_started_at=75.0,
                clean_run_active=True,
            ),
            _saved_state=ControlRoomState(),
            _config=SimpleNamespace(
                control_room=SimpleNamespace(history_limit=20, home_system="Achenar"),
                runtime=SimpleNamespace(platform="macos"),
            ),
            _protocol_activity_log=[
                ActivityLogEntry(
                    entry_id="activity-1",
                    timestamp="2026-07-04T08:00:00Z",
                    message_text="Starting haul loop.",
                    severity="info",
                )
            ],
            _runtime_state=RuntimeUIState(
                routine_active=True,
                active_routine_name="haul",
                haul_phase="transit",
                haul_phase_station_index=2,
            ),
            _current_version="1.2.3",
            _ctx=SimpleNamespace(
                journal=SimpleNamespace(cli_source_status=lambda: "configured"),
                bindings=SimpleNamespace(cli_source_status=lambda: "configured"),
                binding_lookup=None,
            ),
            _time_fn=lambda: 125.0,
        )

        message = hydrate_message(LocalControlRoomDataSource(app).current())

        self.assertEqual(message["schema"], DATA_MESSAGE_SCHEMA)
        self.assertEqual(message["version"], DATA_MESSAGE_VERSION)
        self.assertEqual(message["message_type"], CONTROL_ROOM_HYDRATE)
        self.assertTrue(is_control_room_data_message(message))
        self.assertEqual(message["payload"]["ship"]["system"], "Sol")
        self.assertEqual(message["payload"]["home_system"], "Achenar")
        self.assertEqual(message["payload"]["market"]["station"], "Galileo")
        self.assertEqual(message["payload"]["market"]["market_id"], 3229359104)
        self.assertEqual(message["payload"]["haul_session"]["completed_runs"], 3)
        self.assertEqual(message["payload"]["haul_session"]["cargo_moved_t"], 156)
        self.assertIsNone(message["payload"]["haul_session"]["session_started_at"])
        self.assertEqual(message["payload"]["haul_session"]["session_elapsed_s"], 75.0)
        self.assertIsNone(message["payload"]["haul_session"]["current_run_started_at"])
        self.assertEqual(message["payload"]["haul_session"]["current_run_elapsed_s"], 50.0)
        self.assertEqual(message["payload"]["routine"]["haul_phase"], "transit")
        self.assertEqual(message["payload"]["routine"]["haul_phase_station_index"], 2)
        self.assertEqual(
            message["payload"]["activity_log"]["entries"][0]["message_text"],
            "Starting haul loop.",
        )
        self.assertNotIn("prompt_state", message["payload"])
        self.assertNotIn("replay_browser", message["payload"])

        parsed = data_read_model_from_message(message)

        self.assertEqual(parsed.ship.system, "Sol")
        self.assertEqual(parsed.home_system, "Achenar")
        self.assertEqual(parsed.market.station, "Galileo")
        self.assertEqual(parsed.market.market_id, 3229359104)
        self.assertEqual(parsed.haul_session.completed_runs, 3)
        self.assertEqual(parsed.haul_session.cargo_moved_t, 156)
        self.assertIsNone(parsed.haul_session.session_started_at)
        self.assertEqual(parsed.haul_session.session_elapsed_s, 75.0)
        self.assertEqual(parsed.routine.haul_phase, "transit")
        self.assertEqual(parsed.routine.haul_phase_station_index, 2)
        self.assertEqual(parsed.activity_log.entries[0].message_text, "Starting haul loop.")
