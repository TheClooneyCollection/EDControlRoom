from __future__ import annotations

import unittest

from edap.control_room.routines_haul import _project_two_way_phase
from edap.routines.haul_two_way import Phase


class ControlRoomHaulWebTests(unittest.TestCase):
    def test_two_way_phase_projection_compacts_phase_and_station_for_web(self) -> None:
        self.assertEqual(_project_two_way_phase(Phase.AT_STATION_1_SELL), ("sell", 1))
        self.assertEqual(_project_two_way_phase(Phase.AT_STATION_1_BUY), ("buy", 1))
        self.assertEqual(_project_two_way_phase(Phase.UNDOCK_STATION_2), ("undock", 2))
        self.assertEqual(_project_two_way_phase(Phase.DEPART_STATION_2_SYSTEM), ("depart", 2))
        self.assertEqual(_project_two_way_phase(Phase.TRANSIT_TO_STATION_1), ("transit", 1))
