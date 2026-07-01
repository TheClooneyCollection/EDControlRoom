from __future__ import annotations

import unittest

from edap.control_room.view_actions import MarketPanelViewActions, TradeRoutePickerViewActions
from edap.inara.trade_routes import TradeRoute


class _MarketDependencies:
    def __init__(self) -> None:
        self.tab = "buy"
        self.locked = False
        self.filter_value: str | None = None
        self.notices: list[str] = []
        self.changed_count = 0

    def current_tab(self) -> str:
        return self.tab

    def set_tab_state(self, side: str) -> None:
        self.tab = side

    def set_display_locked(self, locked: bool) -> None:
        self.locked = locked

    def set_filter_state(self, value: str | None) -> None:
        self.filter_value = value

    def append_notice(self, message_text: str) -> None:
        self.notices.append(message_text)

    def market_changed(self) -> None:
        self.changed_count += 1


class _TradeRouteDependencies:
    def __init__(self, routes: list[TradeRoute]) -> None:
        self.routes = routes
        self.selected_index: int | None = routes[0].index if routes else None
        self.open = True
        self.commands: list[str] = []
        self.changed_count = 0
        self.closed_count = 0

    def route_indices(self) -> tuple[int, ...]:
        return tuple(route.index for route in self.routes)

    def selected_route_index(self) -> int | None:
        return self.selected_index

    def set_selected_route_index(self, index: int | None) -> None:
        self.selected_index = index

    def selected_route(self) -> TradeRoute | None:
        return next((route for route in self.routes if route.index == self.selected_index), None)

    def set_picker_open(self, is_open: bool) -> None:
        self.open = is_open

    def submit_command(self, raw: str) -> None:
        self.commands.append(raw)

    def picker_changed(self) -> None:
        self.changed_count += 1

    def picker_closed(self) -> None:
        self.closed_count += 1


class ControlRoomViewActionsTests(unittest.TestCase):
    def test_market_actions_dispatch_through_display_neutral_dependencies(self) -> None:
        dependencies = _MarketDependencies()
        actions = MarketPanelViewActions(dependencies)

        actions.set_tab("sell")
        actions.lock_display()
        actions.set_filter("gold")
        actions.unlock_display()
        actions.clear_filter()

        self.assertEqual(dependencies.tab, "sell")
        self.assertFalse(dependencies.locked)
        self.assertIsNone(dependencies.filter_value)
        self.assertEqual(
            dependencies.notices,
            [
                "Market panel locked.",
                "Market filter: Gold",
                "Market panel unlocked.",
                "Market filter cleared.",
            ],
        )
        self.assertEqual(dependencies.changed_count, 5)

    def test_market_actions_ignore_invalid_or_current_tab(self) -> None:
        dependencies = _MarketDependencies()
        actions = MarketPanelViewActions(dependencies)

        actions.set_tab("inventory")
        actions.set_tab("buy")

        self.assertEqual(dependencies.tab, "buy")
        self.assertEqual(dependencies.changed_count, 0)

    def test_trade_route_actions_move_selection_and_close_picker(self) -> None:
        dependencies = _TradeRouteDependencies(
            routes=[
                TradeRoute(index=1, from_station="A", from_system="Sol", to_station="B", to_system="Sol"),
                TradeRoute(index=2, from_station="C", from_system="Achenar", to_station="D", to_system="Sol"),
            ]
        )
        actions = TradeRoutePickerViewActions(dependencies)

        actions.move_selection(1)
        actions.close()

        self.assertEqual(dependencies.selected_index, 2)
        self.assertFalse(dependencies.open)
        self.assertEqual(dependencies.changed_count, 2)
        self.assertEqual(dependencies.closed_count, 1)

    def test_trade_route_actions_dispatch_selected_route_commands(self) -> None:
        route = TradeRoute(
            index=7,
            from_station="A",
            from_system="TSONGORIS",
            to_station="B",
            to_system="Sol",
        )
        dependencies = _TradeRouteDependencies(routes=[route])
        actions = TradeRoutePickerViewActions(dependencies)

        actions.load_selected()
        dependencies.open = True
        actions.set_destination_for_selected()

        self.assertEqual(dependencies.commands, ["haul route 7", "dest TSONGORIS"])
        self.assertEqual(dependencies.closed_count, 2)


if __name__ == "__main__":
    unittest.main()
