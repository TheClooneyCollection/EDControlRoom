from __future__ import annotations

import unittest
from pathlib import Path

from edap.control_room.routines_haul import _project_two_way_phase
from edap.routines.haul_two_way import Phase


class ControlRoomHaulWebTests(unittest.TestCase):
    def test_two_way_phase_projection_compacts_phase_and_station_for_web(self) -> None:
        self.assertEqual(_project_two_way_phase(Phase.AT_STATION_1_SELL), ("sell", 1))
        self.assertEqual(_project_two_way_phase(Phase.AT_STATION_1_BUY), ("buy", 1))
        self.assertEqual(_project_two_way_phase(Phase.UNDOCK_STATION_2), ("undock", 2))
        self.assertEqual(_project_two_way_phase(Phase.DEPART_STATION_2_SYSTEM), ("depart", 2))
        self.assertEqual(_project_two_way_phase(Phase.TRANSIT_TO_STATION_1), ("transit", 1))

    def test_haul_web_exposes_explicit_stop_controls(self) -> None:
        html = (Path(__file__).resolve().parents[1] / "web" / "haul-v1.html").read_text(encoding="utf-8")

        self.assertIn('id="stop-after-run"', html)
        self.assertIn('id="stop-now"', html)
        self.assertIn('sendCommand("command.cancel_active_routine", { mode })', html)

    def test_haul_web_exposes_instant_mode_toggle(self) -> None:
        html = (Path(__file__).resolve().parents[1] / "web" / "haul-v1.html").read_text(encoding="utf-8")

        self.assertIn('id="instant-toggle"', html)
        self.assertIn("currentRoutine.instant_mode", html)
        self.assertIn('sendCommand("command.submit_input"', html)
        self.assertIn("raw_input: `instant ${nextMode}`", html)

    def test_haul_web_exposes_connection_error_recovery_ui(self) -> None:
        html = (Path(__file__).resolve().parents[1] / "web" / "haul-v1.html").read_text(encoding="utf-8")

        self.assertIn('id="connection-banner"', html)
        self.assertIn('id="reconnect-websocket"', html)
        self.assertIn('id="connection-reconnect"', html)
        self.assertIn("const RECONNECT_INITIAL_DELAY_MS = 1000", html)
        self.assertIn("const RECONNECT_MAX_DELAY_MS = 30000", html)
        self.assertIn("function scheduleReconnect(reason)", html)
        self.assertIn("Math.min(reconnectDelayMs * 2, RECONNECT_MAX_DELAY_MS)", html)
        self.assertIn("event.code === 4401", html)
        self.assertNotIn("|| !receivedConnectionReady", html)

    def test_haul_web_renders_home_and_current_system_from_distinct_hydrate_fields(self) -> None:
        html = (Path(__file__).resolve().parents[1] / "web" / "haul-v1.html").read_text(encoding="utf-8")

        self.assertIn('id="summary-home">-</div>', html)
        self.assertIn('id="summary-current">-</div>', html)
        self.assertIn('document.getElementById("summary-current").textContent = ship.system || "-";', html)
        self.assertIn('document.getElementById("summary-home").textContent = payload.home_system || "-";', html)
        self.assertNotIn("market.station || ship.station || ship.system", html)

    def test_haul_web_activity_log_scrolls_full_hydrated_history(self) -> None:
        html = (Path(__file__).resolve().parents[1] / "web" / "haul-v1.html").read_text(encoding="utf-8")

        self.assertIn(".activity-list", html)
        self.assertIn("overflow-y: auto", html)
        self.assertIn('id="activity-list" role="log" aria-live="polite" tabindex="0"', html)
        self.assertIn("Array.from(activityEntries.values()).reverse()", html)
        self.assertIn('`${entries.length} entries`', html)
        self.assertNotIn("slice(-8)", html)

    def test_haul_web_treats_connected_clients_as_operators(self) -> None:
        html = (Path(__file__).resolve().parents[1] / "web" / "haul-v1.html").read_text(encoding="utf-8")

        self.assertIn('clientRole = "active_operator";', html)
        self.assertIn("Operator connection required", html)
        self.assertNotIn("Only the active operator", html)
        self.assertNotIn("Active operator required", html)
