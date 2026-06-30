from __future__ import annotations

from types import SimpleNamespace
import unittest

from edap.control_room.dependencies import LocalControlRoomDataSource
from edap.control_room.models import HaulStats, MarketData, RuntimeUIState, ShipState
from edap.control_room.protocol.data_messages import (
    CONTROL_ROOM_HYDRATE,
    DATA_MESSAGE_SCHEMA,
    DATA_MESSAGE_VERSION,
    hydrate_message,
    is_control_room_data_message,
)
from edap.control_room_state import ControlRoomState


class ControlRoomDataMessagesTests(unittest.TestCase):
    def test_hydrate_message_wraps_data_source_read_model(self) -> None:
        app = SimpleNamespace(
            _ship=ShipState(system="Sol"),
            _market=MarketData(station="Galileo"),
            _haul_stats=HaulStats(completed_runs=3),
            _saved_state=ControlRoomState(),
            _config=SimpleNamespace(
                control_room=SimpleNamespace(history_limit=20),
                runtime=SimpleNamespace(platform="macos"),
            ),
            _protocol_activity_log=[],
            _runtime_state=RuntimeUIState(),
            _current_version="1.2.3",
            _ctx=SimpleNamespace(
                journal=SimpleNamespace(cli_source_status=lambda: "configured"),
                bindings=SimpleNamespace(cli_source_status=lambda: "configured"),
                binding_lookup=None,
            ),
        )

        message = hydrate_message(LocalControlRoomDataSource(app).current())

        self.assertEqual(message["schema"], DATA_MESSAGE_SCHEMA)
        self.assertEqual(message["version"], DATA_MESSAGE_VERSION)
        self.assertEqual(message["message_type"], CONTROL_ROOM_HYDRATE)
        self.assertTrue(is_control_room_data_message(message))
        self.assertEqual(message["payload"]["ship"]["system"], "Sol")
        self.assertEqual(message["payload"]["market"]["station"], "Galileo")
        self.assertEqual(message["payload"]["haul_session"]["completed_runs"], 3)
        self.assertNotIn("prompt_state", message["payload"])
        self.assertNotIn("replay_browser", message["payload"])
