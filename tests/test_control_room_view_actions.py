from __future__ import annotations

from types import SimpleNamespace
import unittest

from edap.control_room.models import (
    MarketData,
    RuntimeUIState,
    TradeRoutePickerState,
    TradeRoutesData,
)
from edap.control_room.view_actions import LocalMarketPanelActions, LocalTradeRoutePickerActions
from edap.inara.trade_routes import TradeRoute


class ControlRoomViewActionsTests(unittest.TestCase):
    def test_market_actions_update_local_presentation_state(self) -> None:
        logs: list[str] = []
        refreshes: list[str] = []
        app = SimpleNamespace(
            _runtime_state=RuntimeUIState(market_panel_tab="buy"),
            _market=MarketData(),
            _market_filter=None,
            _log=logs.append,
            _refresh_market=lambda: refreshes.append("market"),
        )
        actions = LocalMarketPanelActions(app)

        actions.set_tab("sell")
        actions.lock_display()
        actions.set_filter("gold")
        actions.unlock_display()
        actions.clear_filter()

        self.assertEqual(app._runtime_state.market_panel_tab, "sell")
        self.assertFalse(app._market.locked)
        self.assertIsNone(app._market_filter)
        self.assertEqual(
            logs,
            [
                "[dim]Market panel locked.[/]",
                "[dim]Market filter: Gold[/]",
                "[dim]Market panel unlocked.[/]",
                "[dim]Market filter cleared.[/]",
            ],
        )
        self.assertEqual(refreshes, ["market", "market", "market", "market", "market"])

    def test_trade_route_actions_move_selection_and_close_picker(self) -> None:
        refreshes: list[str] = []
        focused: list[object] = []
        command_input = object()
        app = SimpleNamespace(
            _trade_routes=TradeRoutesData(
                routes=[
                    TradeRoute(index=1, from_station="A", from_system="Sol", to_station="B", to_system="Sol"),
                    TradeRoute(index=2, from_station="C", from_system="Achenar", to_station="D", to_system="Sol"),
                ]
            ),
            _trade_route_picker_state=TradeRoutePickerState(open=True, selected_route_index=1),
            _refresh_trade_route_picker=lambda: refreshes.append("routes"),
            query_one=lambda selector: command_input,
            set_focus=focused.append,
        )
        actions = LocalTradeRoutePickerActions(app)

        actions.move_selection(1)
        actions.close()

        self.assertEqual(app._trade_route_picker_state.selected_route_index, 2)
        self.assertFalse(app._trade_route_picker_state.open)
        self.assertEqual(refreshes, ["routes", "routes"])
        self.assertEqual(focused, [command_input])

    def test_trade_route_actions_dispatch_selected_route_commands(self) -> None:
        dispatched: list[str] = []
        route = TradeRoute(
            index=7,
            from_station="A",
            from_system="TSONGORIS",
            to_station="B",
            to_system="Sol",
        )
        app = SimpleNamespace(
            _trade_routes=TradeRoutesData(routes=[route]),
            _trade_route_picker_state=TradeRoutePickerState(open=True, selected_route_index=7),
            _selected_trade_route=lambda: route,
            _refresh_trade_route_picker=lambda: None,
            _dispatch_command=dispatched.append,
            query_one=lambda selector: object(),
            set_focus=lambda widget: None,
        )
        actions = LocalTradeRoutePickerActions(app)

        actions.load_selected()
        actions.set_destination_for_selected()

        self.assertEqual(dispatched, ["haul route 7", "dest TSONGORIS"])
