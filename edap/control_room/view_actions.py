from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from rich.markup import escape

if TYPE_CHECKING:
    from edap.control_room.app import ControlRoomApp


class MarketPanelActions(Protocol):
    def set_tab(self, side: str) -> None: ...

    def lock_display(self) -> None: ...

    def unlock_display(self) -> None: ...

    def set_filter(self, value: str) -> None: ...

    def clear_filter(self) -> None: ...


@dataclass(frozen=True)
class ControlRoomViewActions:
    market: MarketPanelActions


class LocalMarketPanelActions:
    def __init__(self, app: ControlRoomApp) -> None:
        self._app = app

    def set_tab(self, side: str) -> None:
        if side not in {"buy", "sell"} or self._app._runtime_state.market_panel_tab == side:
            return
        self._app._runtime_state.market_panel_tab = side
        self._app._refresh_market()

    def lock_display(self) -> None:
        self._app._market.locked = True
        self._app._log("[dim]Market panel locked.[/]")
        self._app._refresh_market()

    def unlock_display(self) -> None:
        self._app._market.locked = False
        self._app._log("[dim]Market panel unlocked.[/]")
        self._app._refresh_market()

    def set_filter(self, value: str) -> None:
        self._app._market_filter = value.title()
        self._app._log(f"[dim]Market filter: {escape(self._app._market_filter)}[/]")
        self._app._refresh_market()

    def clear_filter(self) -> None:
        self._app._market_filter = None
        self._app._log("[dim]Market filter cleared.[/]")
        self._app._refresh_market()


def build_local_control_room_view_actions(app: ControlRoomApp) -> ControlRoomViewActions:
    return ControlRoomViewActions(
        market=LocalMarketPanelActions(app),
    )
