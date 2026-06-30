from __future__ import annotations

import unittest

from edap.control_room.models import (
    HaulStats,
    MarketData,
    ShipState,
    TradeRoutePickerState,
    TradeRoutesData,
)
from edap.control_room.view_models import (
    haul_panel_view_model,
    market_panel_view_model,
    status_panel_view_model,
    trade_route_picker_view_model,
)
from edap.inara.trade_routes import TradeRoute


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

    def test_trade_route_picker_view_model_selects_requested_route(self) -> None:
        first = TradeRoute(index=1, from_station="A", from_system="Sol", to_station="B", to_system="Sol")
        second = TradeRoute(index=2, from_station="C", from_system="Sol", to_station="D", to_system="Sol")

        view_model = trade_route_picker_view_model(
            TradeRoutesData(system_name="Sol", searched_at="now", routes=[first, second]),
            TradeRoutePickerState(open=True, selected_route_index=2),
        )

        self.assertEqual(view_model.routes, (first, second))
        self.assertIs(view_model.selected_route, second)
        self.assertEqual(view_model.highlighted_index, 1)
        self.assertTrue(view_model.visible)
        self.assertEqual(view_model.system_name, "Sol")
        self.assertEqual(view_model.searched_at, "now")

    def test_trade_route_picker_view_model_defaults_to_first_loaded_route(self) -> None:
        route = TradeRoute(index=7, from_station="A", from_system="Sol", to_station="B", to_system="Sol")

        view_model = trade_route_picker_view_model(
            TradeRoutesData(routes=[route]),
            TradeRoutePickerState(open=True),
        )

        self.assertIs(view_model.selected_route, route)
        self.assertEqual(view_model.highlighted_index, 0)
        self.assertTrue(view_model.visible)

    def test_trade_route_picker_view_model_hides_when_no_routes_loaded(self) -> None:
        view_model = trade_route_picker_view_model(
            TradeRoutesData(routes=[]),
            TradeRoutePickerState(open=True),
        )

        self.assertEqual(view_model.routes, ())
        self.assertIsNone(view_model.selected_route)
        self.assertIsNone(view_model.highlighted_index)
        self.assertFalse(view_model.visible)
