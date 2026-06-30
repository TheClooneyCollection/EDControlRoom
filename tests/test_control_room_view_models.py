from __future__ import annotations

import unittest

from edap.control_room.models import HaulStats, MarketData, ShipState
from edap.control_room.view_models import (
    haul_panel_view_model,
    market_panel_view_model,
    status_panel_view_model,
)


class ControlRoomViewModelsTests(unittest.TestCase):
    def test_status_panel_view_model_wraps_ship_read_model(self) -> None:
        ship = ShipState(system="Sol", station="Galileo")

        view_model = status_panel_view_model(ship)

        self.assertIs(view_model.ship, ship)

    def test_haul_panel_view_model_carries_balance_context(self) -> None:
        stats = HaulStats(station_1="Galileo", station_1_buying="Gold")

        view_model = haul_panel_view_model(stats, current_balance=123_456)

        self.assertIs(view_model.stats, stats)
        self.assertEqual(view_model.current_balance, 123_456)

    def test_market_panel_view_model_carries_local_presentation_state(self) -> None:
        market = MarketData(station="Galileo", system="Sol")

        view_model = market_panel_view_model(
            market,
            market_filter="gold",
            side="sell",
        )

        self.assertIs(view_model.market, market)
        self.assertEqual(view_model.market_filter, "gold")
        self.assertEqual(view_model.side, "sell")
