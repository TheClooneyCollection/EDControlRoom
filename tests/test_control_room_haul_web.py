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
