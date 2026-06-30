from __future__ import annotations

from types import SimpleNamespace
import unittest

from edap.control_room.models import MarketData, RuntimeUIState
from edap.control_room.view_actions import LocalMarketPanelActions


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
