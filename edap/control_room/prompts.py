from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable
from typing import Protocol

from rich.markup import escape
from textual.widgets import Input

from edap.config import AppConfig
from edap.control_room import error_text
from edap.control_room.models import PromptState, ShipState
from edap.control_room_state import ControlRoomState
from edap.haul_search_config import HaulSearchConfigError, load_haul_search_config
from edap.inara.trade_routes import trade_route_search_defaults


@dataclass(frozen=True)
class DestinationPromptDispatch:
    destination: str
    galaxy_map_settle: float
    skip_delay: bool
    raw_command: str


@dataclass(frozen=True)
class HaulPromptUiState:
    placeholder: str
    value: str = ""


@dataclass(frozen=True)
class HaulConfirmResolution:
    launch_haul_loop: bool
    skip_delay: bool
    raw_command: str
    station_1: str | None = None


@dataclass(frozen=True)
class HaulPromptTransition:
    log_lines: tuple[str, ...] = ()
    ui_state: HaulPromptUiState | None = None
    launch_haul_loop: bool = False
    skip_delay: bool = False
    raw_command: str = ""


@dataclass(frozen=True)
class HaulSearchPromptTransition:
    log_lines: tuple[str, ...] = ()
    ui_state: HaulPromptUiState | None = None
    launch_haul_search: bool = False
    system_name: str = ""
    query_params: dict[str, str] = field(default_factory=dict)
    skip_delay: bool = False
    raw_command: str = ""


class PromptHost(Protocol):
    _config: AppConfig
    _prompt_state: PromptState
    _saved_state: ControlRoomState
    _ship: ShipState
    _haul_params: dict[str, str]
    _haul_prompt_defaults: dict[str, str]
    _haul_prompt_step: str
    _haul_prompt_mode: str
    _haul_confirm_buy_station: str
    _haul_prompt_raw_command: str
    _haul_prompt_skip_delay: bool
    _dest_prompt_destination: str
    _dest_prompt_settle_default: float | None
    _dest_prompt_raw_command: str
    _dest_prompt_skip_delay: bool

    def _log(self, msg: str) -> None: ...
    def _dispatch_haul_loop(
        self,
        *,
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None: ...
    def _dispatch_haul_search(
        self,
        *,
        system_name: str,
        query_params: dict[str, str],
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None: ...
    def _dispatch_dest(
        self,
        destination: str,
        galaxy_map_settle: float,
        *,
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None: ...
    def query_one(self, selector: str, widget_type: type[Input]) -> Input: ...


def start_dest_prompt(
    app: PromptHost,
    destination: str,
    *,
    settle_default: float | None = None,
    skip_delay: bool = False,
    raw_command: str | None = None,
) -> None:
    default_settle = begin_destination_prompt(
        app._prompt_state,
        configured_settle_default=app._config.controls.galaxy_map_settle_seconds,
        destination=destination,
        settle_default=settle_default,
        skip_delay=skip_delay,
        raw_command=raw_command,
    )
    app._log(f"Destination: [bold]{escape(destination)}[/]")
    app._log(f"[dim]Galaxy-map settle seconds? (Enter = {default_settle:.1f})[/]")
    app.query_one("#cmd", Input).placeholder = (
        f"galaxy map settle seconds (Enter = {default_settle:.1f})..."
    )


def begin_destination_prompt(
    prompt_state: PromptState,
    *,
    configured_settle_default: float,
    destination: str,
    settle_default: float | None = None,
    skip_delay: bool = False,
    raw_command: str | None = None,
) -> float:
    prompt_state.dest_prompt_destination = destination
    prompt_state.dest_prompt_settle_default = (
        settle_default if settle_default is not None else configured_settle_default
    )
    prompt_state.dest_prompt_raw_command = (
        raw_command or f"{'!' if skip_delay else ''}dest {destination}"
    )
    prompt_state.dest_prompt_skip_delay = skip_delay
    return prompt_state.dest_prompt_settle_default or 0.0


def resolve_destination_prompt_submission(
    prompt_state: PromptState,
    raw: str,
    *,
    parse_optional_nonnegative_float: Callable[[str, float, str], float | None],
) -> DestinationPromptDispatch | None:
    destination = prompt_state.dest_prompt_destination
    if not destination:
        return None
    parsed = parse_optional_nonnegative_float(
        raw,
        prompt_state.dest_prompt_settle_default or 0.0,
        "Galaxy-map settle seconds",
    )
    if parsed is None:
        return None
    raw_command = prompt_state.dest_prompt_raw_command
    skip_delay = prompt_state.dest_prompt_skip_delay
    clear_destination_prompt(prompt_state)
    return DestinationPromptDispatch(
        destination=destination,
        galaxy_map_settle=parsed,
        skip_delay=skip_delay,
        raw_command=raw_command,
    )


def clear_destination_prompt(prompt_state: PromptState) -> None:
    prompt_state.dest_prompt_destination = ""
    prompt_state.dest_prompt_settle_default = None
    prompt_state.dest_prompt_raw_command = ""
    prompt_state.dest_prompt_skip_delay = False


def clear_haul_prompt(prompt_state: PromptState) -> None:
    prompt_state.haul_params = {}
    prompt_state.haul_search_params = {}
    prompt_state.haul_prompt_defaults = {}
    prompt_state.haul_search_prompt_defaults = {}
    prompt_state.haul_prompt_step = ""
    prompt_state.haul_prompt_mode = ""
    prompt_state.haul_prompt_raw_command = ""
    prompt_state.haul_prompt_skip_delay = False


def clear_haul_confirm_prompt(prompt_state: PromptState) -> None:
    prompt_state.haul_confirm_buy_station = ""
    prompt_state.haul_prompt_raw_command = ""
    prompt_state.haul_prompt_skip_delay = False


def saved_haul_defaults(
    app: PromptHost,
    seed: dict[str, str] | None = None,
) -> dict[str, str]:
    defaults = dict(app._saved_state.default_haul)
    if seed:
        defaults.update({str(key): str(value) for key, value in seed.items()})
    if not defaults.get("station_1") and app._ship.station:
        defaults["station_1"] = app._ship.station
    if not defaults.get("station_1_system") and app._ship.system:
        defaults["station_1_system"] = app._ship.system
    if not defaults.get("galaxy_map_settle"):
        defaults["galaxy_map_settle"] = str(app._config.controls.galaxy_map_settle_seconds)
    if not defaults.get("dock_timeout"):
        defaults["dock_timeout"] = str(app._config.controls.haul_dock_timeout_seconds)
    return defaults


def saved_haul_search_defaults(
    app: PromptHost,
    *,
    system_name: str,
    seed: dict[str, str] | None = None,
) -> dict[str, str]:
    defaults = trade_route_search_defaults()
    try:
        defaults.update(load_haul_search_config())
    except FileNotFoundError:
        pass
    if seed:
        defaults.update({str(key): str(value) for key, value in seed.items()})
    defaults["near_system"] = system_name.strip()
    if app._ship.cargo_capacity:
        defaults["cargo_capacity"] = str(app._ship.cargo_capacity)
    return defaults


def _set_prompt_input(
    app: PromptHost,
    *,
    placeholder: str,
    value: str = "",
) -> None:
    cmd_input = app.query_one("#cmd", Input)
    cmd_input.placeholder = placeholder
    cmd_input.value = value
    cmd_input.cursor_position = len(value)


def cancel_prompt_flow(
    app: PromptHost,
    *,
    default_placeholder: str,
    source: str,
) -> bool:
    if app._haul_prompt_step:
        clear_haul_prompt(app._prompt_state)
        _set_prompt_input(app, placeholder=default_placeholder)
        app._log(f"[yellow]{escape(source)} received — cancelling haul prompt.[/]")
        return True
    if app._haul_confirm_buy_station:
        clear_haul_confirm_prompt(app._prompt_state)
        _set_prompt_input(app, placeholder=default_placeholder)
        app._log(f"[yellow]{escape(source)} received — cancelling haul confirmation.[/]")
        return True
    if app._dest_prompt_destination:
        clear_destination_prompt(app._prompt_state)
        _set_prompt_input(app, placeholder=default_placeholder)
        app._log(f"[yellow]{escape(source)} received — cancelling destination prompt.[/]")
        return True
    return False


def _prefill_value(
    app: PromptHost,
    key: str,
) -> str:
    return _prefill_value_from_state(app._prompt_state, key)


def _prefill_value_from_state(
    prompt_state: PromptState,
    key: str,
) -> str:
    current = prompt_state.haul_params.get(key, "")
    if current:
        return current
    return prompt_state.haul_prompt_defaults.get(key, "")


def _search_prefill_value_from_state(
    prompt_state: PromptState,
    key: str,
) -> str:
    current = prompt_state.haul_search_params.get(key, "")
    if current:
        return current
    return prompt_state.haul_search_prompt_defaults.get(key, "")


def _parse_yes_no(value: str, *, default: bool) -> bool | None:
    raw = value.strip().lower()
    if not raw:
        return default
    if raw in {"y", "yes", "true", "1", "land", "surface"}:
        return True
    if raw in {"n", "no", "false", "0", "station", "orbital"}:
        return False
    return None


def _search_choice_label(value: str, labels: dict[str, str]) -> str:
    return labels.get(value, value)


_LANDING_PAD_LABELS = {
    "small": "Small",
    "medium": "Medium",
    "large": "Large",
}

_SURFACE_STATION_LABELS = {
    "yes_with_odyssey": "Yes (with Odyssey stations)",
    "no": "No",
    "yes_exclude_odyssey": "Yes (exclude Odyssey stations)",
}

_ORDER_BY_LABELS = {
    "best_profit": "Best profit",
    "last_update": "Last update",
    "route_distance": "Route distance",
    "distance": "Distance",
    "best_profit_per_hour_estimate": "Best profit per hour (estimate)",
}


def _parse_search_landing_pad(value: str, *, default: str) -> str | None:
    raw = value.strip().lower().replace("pad", "")
    if not raw:
        return default
    aliases = {
        "s": "small",
        "small": "small",
        "m": "medium",
        "medium": "medium",
        "l": "large",
        "large": "large",
    }
    return aliases.get(raw)


def _parse_surface_stations(value: str, *, default: str) -> str | None:
    raw = value.strip().lower().replace(" ", "_").replace("-", "_")
    if not raw:
        return default
    aliases = {
        "no": "no",
        "n": "no",
        "yes": "yes_with_odyssey",
        "y": "yes_with_odyssey",
        "yes_with_odyssey": "yes_with_odyssey",
        "with_odyssey": "yes_with_odyssey",
        "odyssey": "yes_with_odyssey",
        "yes_exclude_odyssey": "yes_exclude_odyssey",
        "exclude_odyssey": "yes_exclude_odyssey",
        "without_odyssey": "yes_exclude_odyssey",
    }
    return aliases.get(raw)


def _parse_order_by(value: str, *, default: str) -> str | None:
    raw = value.strip().lower().replace(" ", "_").replace("-", "_")
    if not raw:
        return default
    aliases = {
        "best_profit": "best_profit",
        "profit": "best_profit",
        "last_update": "last_update",
        "update": "last_update",
        "route_distance": "route_distance",
        "route": "route_distance",
        "distance": "distance",
        "best_profit_per_hour_estimate": "best_profit_per_hour_estimate",
        "best_profit_per_hour": "best_profit_per_hour_estimate",
        "profit_per_hour": "best_profit_per_hour_estimate",
        "hour": "best_profit_per_hour_estimate",
    }
    return aliases.get(raw)


def begin_haul_prompt(
    prompt_state: PromptState,
    *,
    commodity: str,
    prompt_for_commodity: bool,
    haul_prompt_defaults: dict[str, str],
    current_station: str | None,
    raw_command: str,
    skip_delay: bool,
) -> HaulPromptUiState:
    prompt_state.haul_params = {
        "station_1_buying": commodity.strip(),
        "station_1": "",
        "station_1_system": "",
        "station_1_on_land": "",
        "station_2_buying": "",
        "station_2": "",
        "station_2_system": "",
        "station_2_on_land": "",
        "galaxy_map_settle": "",
        "dock_timeout": "",
    }
    prompt_state.haul_prompt_raw_command = raw_command
    prompt_state.haul_prompt_skip_delay = skip_delay
    prompt_state.haul_prompt_defaults = dict(haul_prompt_defaults)
    if prompt_for_commodity:
        prompt_state.haul_prompt_step = "station_1_buying"
        default_commodity = prompt_state.haul_prompt_defaults.get("station_1_buying", "")
        if default_commodity:
            return HaulPromptUiState(
                placeholder=f"station 1 buying (Enter = {default_commodity})...",
                value=default_commodity,
            )
        return HaulPromptUiState(placeholder="station 1 buying...")

    prompt_state.haul_prompt_step = "station_1"
    default_station_1 = prompt_state.haul_prompt_defaults.get("station_1", "")
    if default_station_1:
        return HaulPromptUiState(
            placeholder=f"station 1 (Enter = {default_station_1})...",
            value=default_station_1,
        )
    current = current_station or "current station"
    return HaulPromptUiState(
        placeholder=f"station 1 (Enter = {current})...",
    )


def resolve_haul_confirm_prompt(
    prompt_state: PromptState,
    value: str,
) -> HaulConfirmResolution | None:
    answer = value.strip().lower()
    if answer in {"", "y", "yes"}:
        station = prompt_state.haul_confirm_buy_station
        prompt_state.haul_confirm_buy_station = ""
        prompt_state.haul_params["station_1"] = station
        return HaulConfirmResolution(
            launch_haul_loop=True,
            station_1=station,
            skip_delay=prompt_state.haul_prompt_skip_delay,
            raw_command=prompt_state.haul_prompt_raw_command,
        )
    if answer in {"n", "no"}:
        station = prompt_state.haul_confirm_buy_station
        clear_haul_confirm_prompt(prompt_state)
        return HaulConfirmResolution(
            launch_haul_loop=False,
            station_1=station,
            skip_delay=False,
            raw_command="",
        )
    return None


def advance_haul_prompt(
    prompt_state: PromptState,
    value: str,
    *,
    current_station: str | None,
    current_system: str | None,
    configured_galaxy_map_settle_default: float,
    configured_dock_timeout_default: float,
    default_placeholder: str,
    render_error: Callable[..., str],
    parse_optional_nonnegative_float: Callable[[str, float, str], float | None],
) -> HaulPromptTransition:
    if prompt_state.haul_prompt_step == "station_1_buying":
        resolved = value.strip()
        prompt_state.haul_params["station_1_buying"] = resolved
        prompt_state.haul_prompt_step = "station_1"
        default_station_1 = prompt_state.haul_prompt_defaults.get("station_1", "")
        if default_station_1:
            return HaulPromptTransition(
                log_lines=(
                    f"  Station 1 buying: [cyan]{escape(resolved)}[/]"
                    if resolved
                    else "  Station 1 buying: [dim](none)[/]",
                    f"[dim]Station 1 name? (Enter = {escape(default_station_1)})[/]",
                ),
                ui_state=HaulPromptUiState(
                    placeholder=f"station 1 (Enter = {default_station_1})...",
                    value=_prefill_value_from_state(prompt_state, "station_1"),
                ),
            )
        current = current_station or "current station"
        return HaulPromptTransition(
            log_lines=(
                f"  Station 1 buying: [cyan]{escape(resolved)}[/]"
                if resolved
                else "  Station 1 buying: [dim](none)[/]",
                f"[dim]Station 1 name? (Enter to use {escape(current)})[/]",
            ),
            ui_state=HaulPromptUiState(
                placeholder=f"station 1 (Enter = {current})...",
                value=_prefill_value_from_state(prompt_state, "station_1"),
            ),
        )

    if prompt_state.haul_prompt_step == "station_1":
        resolved = value.strip()
        prompt_state.haul_params["station_1"] = resolved
        prompt_state.haul_prompt_step = "station_1_system"
        default_station_1_system = prompt_state.haul_prompt_defaults.get("station_1_system", "")
        station_log = (
            f"  Station 1: [cyan]{escape(resolved)}[/]"
            if resolved
            else "  Station 1: [dim](current station)[/]"
        )
        if default_station_1_system:
            return HaulPromptTransition(
                log_lines=(
                    station_log,
                    f"[dim]Station 1 system? (Enter = {escape(default_station_1_system)})[/]",
                ),
                ui_state=HaulPromptUiState(
                    placeholder=f"station 1 system (Enter = {default_station_1_system})...",
                    value=_prefill_value_from_state(prompt_state, "station_1_system"),
                ),
            )
        current = current_system or "current system"
        return HaulPromptTransition(
            log_lines=(
                station_log,
                f"[dim]Station 1 system? (Enter to use {escape(current)})[/]",
            ),
            ui_state=HaulPromptUiState(
                placeholder=f"station 1 system (Enter = {current})...",
                value=_prefill_value_from_state(prompt_state, "station_1_system"),
            ),
        )

    if prompt_state.haul_prompt_step == "station_1_system":
        resolved = value.strip()
        prompt_state.haul_params["station_1_system"] = resolved
        prompt_state.haul_prompt_step = "station_1_on_land"
        default_station_1_on_land = _parse_yes_no(
            prompt_state.haul_prompt_defaults.get("station_1_on_land", ""),
            default=False,
        )
        default_label = "yes" if default_station_1_on_land else "no"
        return HaulPromptTransition(
            log_lines=(
                f"  Station 1 system: [cyan]{escape(resolved)}[/]"
                if resolved
                else "  Station 1 system: [dim](current system)[/]",
                f"[dim]Station 1 on land? (Enter = {default_label}; yes for settlement/manual landing)[/]",
            ),
            ui_state=HaulPromptUiState(
                placeholder=f"station 1 on land? (Enter = {default_label})...",
                value=_prefill_value_from_state(prompt_state, "station_1_on_land"),
            ),
        )

    if prompt_state.haul_prompt_step == "station_1_on_land":
        default_station_1_on_land = _parse_yes_no(
            prompt_state.haul_prompt_defaults.get("station_1_on_land", ""),
            default=False,
        )
        parsed = _parse_yes_no(value, default=bool(default_station_1_on_land))
        if parsed is None:
            return HaulPromptTransition(
                log_lines=(f"[red]{escape(render_error('confirm_yes_no'))}[/]",),
            )
        prompt_state.haul_params["station_1_on_land"] = "true" if parsed else "false"
        prompt_state.haul_prompt_step = "station_2_buying"
        default_station_2_buying = prompt_state.haul_prompt_defaults.get("station_2_buying", "")
        if default_station_2_buying:
            return HaulPromptTransition(
                log_lines=(
                    f"  Station 1 on land: [cyan]{'yes' if parsed else 'no'}[/]",
                    f"[dim]Station 2 buying? (optional, Enter = {escape(default_station_2_buying)})[/]",
                ),
                ui_state=HaulPromptUiState(
                    placeholder=f"station 2 buying (Enter = {default_station_2_buying})...",
                    value=_prefill_value_from_state(prompt_state, "station_2_buying"),
                ),
            )
        return HaulPromptTransition(
            log_lines=(
                f"  Station 1 on land: [cyan]{'yes' if parsed else 'no'}[/]",
                "[dim]Station 2 buying? (optional; this cargo will be sold at station 1)[/]",
            ),
            ui_state=HaulPromptUiState(
                placeholder="station 2 buying...",
                value=_prefill_value_from_state(prompt_state, "station_2_buying"),
            ),
        )

    if prompt_state.haul_prompt_step == "station_2_buying":
        resolved = value.strip()
        prompt_state.haul_params["station_2_buying"] = resolved
        prompt_state.haul_prompt_step = "station_2"
        default_station_2 = prompt_state.haul_prompt_defaults.get("station_2", "")
        if default_station_2:
            return HaulPromptTransition(
                log_lines=(
                    f"  Station 2 buying: [cyan]{escape(resolved)}[/]"
                    if resolved
                    else "  Station 2 buying: [dim](none)[/]",
                    f"[dim]Station 2 name? (Enter = {escape(default_station_2)})[/]",
                ),
                ui_state=HaulPromptUiState(
                    placeholder=f"station 2 (Enter = {default_station_2})...",
                    value=_prefill_value_from_state(prompt_state, "station_2"),
                ),
            )
        return HaulPromptTransition(
            log_lines=(
                f"  Station 2 buying: [cyan]{escape(resolved)}[/]"
                if resolved
                else "  Station 2 buying: [dim](none)[/]",
                "[dim]Station 2 name?[/]",
            ),
            ui_state=HaulPromptUiState(
                placeholder="station 2...",
                value=_prefill_value_from_state(prompt_state, "station_2"),
            ),
        )

    if prompt_state.haul_prompt_step == "station_2":
        resolved = value.strip()
        if not resolved:
            return HaulPromptTransition(
                log_lines=(f"[red]{escape(render_error('station_2_name_required'))}[/]",),
            )
        prompt_state.haul_params["station_2"] = resolved
        prompt_state.haul_prompt_step = "station_2_system"
        default_station_2_system = prompt_state.haul_prompt_defaults.get("station_2_system", "")
        if default_station_2_system:
            return HaulPromptTransition(
                log_lines=(
                    f"  Station 2: [cyan]{escape(resolved)}[/]",
                    f"[dim]Station 2 system? (Enter = {escape(default_station_2_system)})[/]",
                ),
                ui_state=HaulPromptUiState(
                    placeholder=f"station 2 system (Enter = {default_station_2_system})...",
                    value=_prefill_value_from_state(prompt_state, "station_2_system"),
                ),
            )
        return HaulPromptTransition(
            log_lines=(
                f"  Station 2: [cyan]{escape(resolved)}[/]",
                "[dim]Station 2 system?[/]",
            ),
            ui_state=HaulPromptUiState(
                placeholder="station 2 system...",
                value=_prefill_value_from_state(prompt_state, "station_2_system"),
            ),
        )

    if prompt_state.haul_prompt_step == "station_2_system":
        resolved = value.strip()
        if not resolved:
            return HaulPromptTransition(
                log_lines=(f"[red]{escape(render_error('station_2_system_required'))}[/]",),
            )
        prompt_state.haul_params["station_2_system"] = resolved
        prompt_state.haul_prompt_step = "station_2_on_land"
        default_station_2_on_land = _parse_yes_no(
            prompt_state.haul_prompt_defaults.get("station_2_on_land", ""),
            default=False,
        )
        default_label = "yes" if default_station_2_on_land else "no"
        return HaulPromptTransition(
            log_lines=(
                f"  Station 2 system: [cyan]{escape(resolved)}[/]",
                f"[dim]Station 2 on land? (Enter = {default_label}; yes for settlement/manual landing)[/]",
            ),
            ui_state=HaulPromptUiState(
                placeholder=f"station 2 on land? (Enter = {default_label})...",
                value=_prefill_value_from_state(prompt_state, "station_2_on_land"),
            ),
        )

    if prompt_state.haul_prompt_step == "station_2_on_land":
        default_station_2_on_land = _parse_yes_no(
            prompt_state.haul_prompt_defaults.get("station_2_on_land", ""),
            default=False,
        )
        parsed = _parse_yes_no(value, default=bool(default_station_2_on_land))
        if parsed is None:
            return HaulPromptTransition(
                log_lines=(f"[red]{escape(render_error('confirm_yes_no'))}[/]",),
            )
        prompt_state.haul_params["station_2_on_land"] = "true" if parsed else "false"
        default_settle = float(
            prompt_state.haul_prompt_defaults.get(
                "galaxy_map_settle",
                configured_galaxy_map_settle_default,
            )
        )
        prompt_state.haul_prompt_step = "galaxy_map_settle"
        return HaulPromptTransition(
            log_lines=(
                f"  Station 2 on land: [cyan]{'yes' if parsed else 'no'}[/]",
                f"[dim]Galaxy-map settle seconds? (Enter = {default_settle:.1f})[/]",
            ),
            ui_state=HaulPromptUiState(
                placeholder=f"galaxy map settle seconds (Enter = {default_settle:.1f})...",
                value=prompt_state.haul_params.get("galaxy_map_settle", "") or str(default_settle),
            ),
        )

    if prompt_state.haul_prompt_step == "galaxy_map_settle":
        parsed = parse_optional_nonnegative_float(
            value,
            float(
                prompt_state.haul_prompt_defaults.get(
                    "galaxy_map_settle",
                    configured_galaxy_map_settle_default,
                )
            ),
            "Galaxy-map settle seconds",
        )
        if parsed is None:
            return HaulPromptTransition()
        prompt_state.haul_params["galaxy_map_settle"] = str(parsed)
        default_timeout = float(
            prompt_state.haul_prompt_defaults.get(
                "dock_timeout",
                configured_dock_timeout_default,
            )
        )
        prompt_state.haul_prompt_step = "dock_timeout"
        return HaulPromptTransition(
            log_lines=(
                f"  Galaxy-map settle: [cyan]{parsed:.1f}s[/]",
                f"[dim]Haul docking timeout seconds? (Enter = {default_timeout:.1f})[/]",
            ),
            ui_state=HaulPromptUiState(
                placeholder=f"haul docking timeout seconds (Enter = {default_timeout:.1f})...",
                value=prompt_state.haul_params.get("dock_timeout", "") or str(default_timeout),
            ),
        )

    if prompt_state.haul_prompt_step == "dock_timeout":
        parsed = parse_optional_nonnegative_float(
            value,
            float(
                prompt_state.haul_prompt_defaults.get(
                    "dock_timeout",
                    configured_dock_timeout_default,
                )
            ),
            "Haul docking timeout seconds",
        )
        if parsed is None:
            return HaulPromptTransition()
        prompt_state.haul_params["dock_timeout"] = str(parsed)
        prompt_state.haul_prompt_step = ""
        prompt_state.haul_prompt_defaults = {}
        return HaulPromptTransition(
            log_lines=(f"  Haul docking timeout: [cyan]{parsed:.1f}s[/]",),
            ui_state=HaulPromptUiState(placeholder=default_placeholder),
            launch_haul_loop=True,
            skip_delay=prompt_state.haul_prompt_skip_delay,
            raw_command=prompt_state.haul_prompt_raw_command,
        )

    return HaulPromptTransition()


def start_haul_prompt(
    app: PromptHost,
    *,
    commodity: str,
    prompt_for_commodity: bool,
    seed: dict[str, str] | None = None,
    skip_delay: bool = False,
    raw_command: str | None = None,
) -> None:
    resolved_raw_command = raw_command or f"{'!' if skip_delay else ''}haul {commodity}".strip()
    defaults = saved_haul_defaults(app, seed)
    ui_state = begin_haul_prompt(
        app._prompt_state,
        commodity=commodity,
        prompt_for_commodity=prompt_for_commodity,
        haul_prompt_defaults=defaults,
        current_station=app._ship.station,
        raw_command=resolved_raw_command,
        skip_delay=skip_delay,
    )
    app._log("Haul loop setup — enter parameters below:")
    if prompt_for_commodity:
        default_commodity = defaults.get("station_1_buying", "")
        if default_commodity:
            app._log(f"[dim]Station 1 buying? (optional, Enter = {escape(default_commodity)})[/]")
        else:
            app._log("[dim]Station 1 buying? (optional; this cargo will be sold at station 2)[/]")
        _set_prompt_input(app, placeholder=ui_state.placeholder, value=ui_state.value)
        return

    app._log(
        f"Haul loop: station 1 buying = [cyan]{escape(app._haul_params['station_1_buying'])}[/]"
    )
    default_station_1 = defaults.get("station_1", "")
    if default_station_1:
        app._log(f"[dim]Station 1 name? (Enter = {escape(default_station_1)})[/]")
    else:
        current = app._ship.station or "current station"
        app._log(f"[dim]Station 1 name? (Enter to use {escape(current)})[/]")
    _set_prompt_input(app, placeholder=ui_state.placeholder, value=ui_state.value)


def start_haul_search_prompt(
    app: PromptHost,
    *,
    system_name: str,
    seed: dict[str, str] | None = None,
    skip_delay: bool = False,
    raw_command: str | None = None,
) -> None:
    resolved_raw_command = (
        raw_command or f"{'!' if skip_delay else ''}haul search {system_name}".strip()
    )
    try:
        defaults = saved_haul_search_defaults(app, system_name=system_name, seed=seed)
    except HaulSearchConfigError as exc:
        app._log(f"[red]{escape(str(exc))}[/]")
        return

    app._prompt_state.haul_params = {}
    app._prompt_state.haul_search_params = {}
    app._prompt_state.haul_prompt_defaults = {}
    app._prompt_state.haul_search_prompt_defaults = defaults
    app._prompt_state.haul_prompt_mode = "search"
    app._prompt_state.haul_prompt_step = "search_near_system"
    app._prompt_state.haul_prompt_raw_command = resolved_raw_command
    app._prompt_state.haul_prompt_skip_delay = skip_delay
    default_system = defaults["near_system"]

    app._log("Haul search setup — edit Inara parameters below:")
    app._log(f"[dim]Near star system? (Enter = {escape(default_system)})[/]")
    _set_prompt_input(
        app,
        placeholder=f"near star system (Enter = {default_system})...",
        value=_search_prefill_value_from_state(app._prompt_state, "near_system") or default_system,
    )


def start_haul_confirm_prompt(
    app: PromptHost,
    station: str,
) -> None:
    app._haul_confirm_buy_station = station
    app._log(
        f"[dim]Assume current station [cyan]{escape(station)}[/] is station 1? "
        f"(Enter = yes, no to cancel)[/]"
    )
    _set_prompt_input(
        app,
        placeholder="confirm station 1? Enter = yes, no to cancel...",
    )


def handle_haul_confirm_prompt(
    app: PromptHost,
    value: str,
    *,
    default_placeholder: str,
) -> None:
    resolution = resolve_haul_confirm_prompt(app._prompt_state, value)
    if resolution is None:
        app._log(f"[red]{escape(error_text.render(app._config, 'confirm_yes_no'))}[/]")
        return
    if resolution.launch_haul_loop:
        station = resolution.station_1 or ""
        app._log(f"  Station 1 confirmed: [cyan]{escape(station)}[/]")
        _set_prompt_input(app, placeholder=default_placeholder)
        app._dispatch_haul_loop(
            skip_delay=resolution.skip_delay,
            raw_command=resolution.raw_command,
        )
        return
    if resolution.station_1 is not None:
        station = resolution.station_1
        app._log(
            f"[yellow]Haul launch cancelled — station 1 left unresolved "
            f"for [cyan]{escape(station)}[/].[/]"
        )
        _set_prompt_input(app, placeholder=default_placeholder)
        return


def handle_haul_prompt(
    app: PromptHost,
    value: str,
    *,
    default_placeholder: str,
) -> None:
    if app._prompt_state.haul_prompt_mode == "search":
        transition = advance_haul_search_prompt(
            app,
            value,
            default_placeholder=default_placeholder,
        )
        for line in transition.log_lines:
            app._log(line)
        if transition.ui_state is not None:
            _set_prompt_input(
                app,
                placeholder=transition.ui_state.placeholder,
                value=transition.ui_state.value,
            )
        if transition.launch_haul_search:
            app._dispatch_haul_search(
                system_name=transition.system_name,
                query_params=transition.query_params,
                skip_delay=transition.skip_delay,
                raw_command=transition.raw_command,
            )
        return

    transition = advance_haul_prompt(
        app._prompt_state,
        value,
        current_station=app._ship.station,
        current_system=app._ship.system,
        configured_galaxy_map_settle_default=app._config.controls.galaxy_map_settle_seconds,
        configured_dock_timeout_default=app._config.controls.haul_dock_timeout_seconds,
        default_placeholder=default_placeholder,
        render_error=lambda key, **kwargs: error_text.render(app._config, key, **kwargs),
        parse_optional_nonnegative_float=lambda raw_value, default, label: (
            parse_optional_nonnegative_float(
                app,
                raw_value,
                default=default,
                label=label,
            )
        ),
    )
    for line in transition.log_lines:
        app._log(line)
    if transition.ui_state is not None:
        _set_prompt_input(
            app,
            placeholder=transition.ui_state.placeholder,
            value=transition.ui_state.value,
        )
    if transition.launch_haul_loop:
        app._dispatch_haul_loop(
            skip_delay=transition.skip_delay,
            raw_command=transition.raw_command,
        )


def advance_haul_search_prompt(
    app: PromptHost,
    value: str,
    *,
    default_placeholder: str,
) -> HaulSearchPromptTransition:
    prompt_state = app._prompt_state
    defaults = prompt_state.haul_search_prompt_defaults

    def resolved_default(key: str) -> str:
        return defaults.get(key, "")

    if prompt_state.haul_prompt_step == "search_near_system":
        resolved = value.strip() or resolved_default("near_system")
        if not resolved:
            return HaulSearchPromptTransition(
                log_lines=("[red]Near star system is required.[/]",),
            )
        prompt_state.haul_search_params["near_system"] = resolved
        prompt_state.haul_prompt_step = "search_cargo_capacity"
        default_value = resolved_default("cargo_capacity")
        return HaulSearchPromptTransition(
            log_lines=(
                f"  Near star system: [cyan]{escape(resolved)}[/]",
                f"[dim]Cargo capacity? (Enter = {escape(default_value)})[/]",
            ),
            ui_state=HaulPromptUiState(
                placeholder=f"cargo capacity (Enter = {default_value})...",
                value=_search_prefill_value_from_state(prompt_state, "cargo_capacity") or default_value,
            ),
        )

    numeric_steps = {
        "search_cargo_capacity": ("cargo_capacity", "Cargo capacity", "search_max_route_distance_ly"),
        "search_max_route_distance_ly": (
            "max_route_distance_ly",
            "Max. route distance (Ly)",
            "search_max_price_age_hours",
        ),
        "search_max_price_age_hours": (
            "max_price_age_hours",
            "Max. price age (hours)",
            "search_min_landing_pad",
        ),
        "search_max_station_distance_ls": (
            "max_station_distance_ls",
            "Max. station distance (Ls)",
            "search_use_surface_stations",
        ),
        "search_min_supply": ("min_supply", "Min. supply", "search_min_demand"),
        "search_min_demand": ("min_demand", "Min. demand", "search_include_round_trips"),
    }
    if prompt_state.haul_prompt_step in numeric_steps:
        key, label, next_step = numeric_steps[prompt_state.haul_prompt_step]
        parsed = parse_optional_nonnegative_int(app, value, default=resolved_default(key), label=label)
        if parsed is None:
            return HaulSearchPromptTransition()
        prompt_state.haul_search_params[key] = parsed
        prompt_state.haul_prompt_step = next_step

        if next_step == "search_max_route_distance_ly":
            default_value = resolved_default("max_route_distance_ly")
            prompt_label = "Max. route distance? (Ly)"
            placeholder = f"max route distance ly (Enter = {default_value})..."
            next_key = "max_route_distance_ly"
        elif next_step == "search_max_price_age_hours":
            default_value = resolved_default("max_price_age_hours")
            prompt_label = "Max. price age? (hours)"
            placeholder = f"max price age hours (Enter = {default_value})..."
            next_key = "max_price_age_hours"
        elif next_step == "search_use_surface_stations":
            default_value = resolved_default("use_surface_stations")
            label_value = _search_choice_label(default_value, _SURFACE_STATION_LABELS)
            return HaulSearchPromptTransition(
                log_lines=(
                    f"  {escape(label)}: [cyan]{escape(parsed)}[/]",
                    f"[dim]Use surface stations? (Enter = {escape(label_value)})[/]",
                ),
                ui_state=HaulPromptUiState(
                    placeholder=f"use surface stations (Enter = {label_value})...",
                    value=_search_prefill_value_from_state(prompt_state, "use_surface_stations")
                    or default_value,
                ),
            )
        elif next_step == "search_min_demand":
            default_value = resolved_default("min_demand")
            prompt_label = "Min. demand?"
            placeholder = f"min demand (Enter = {default_value})..."
            next_key = "min_demand"
        else:
            default_value = resolved_default("min_supply")
            prompt_label = "Min. supply?"
            placeholder = f"min supply (Enter = {default_value})..."
            next_key = "min_supply"

        return HaulSearchPromptTransition(
            log_lines=(
                f"  {escape(label)}: [cyan]{escape(parsed)}[/]",
                f"[dim]{escape(prompt_label)} (Enter = {escape(default_value)})[/]",
            ),
            ui_state=HaulPromptUiState(
                placeholder=placeholder,
                value=_search_prefill_value_from_state(prompt_state, next_key) or default_value,
            ),
        )

    if prompt_state.haul_prompt_step == "search_min_landing_pad":
        default_value = resolved_default("min_landing_pad")
        parsed = _parse_search_landing_pad(value, default=default_value)
        if parsed is None:
            return HaulSearchPromptTransition(
                log_lines=("[red]Min. landing pad must be small, medium, or large.[/]",),
            )
        prompt_state.haul_search_params["min_landing_pad"] = parsed
        prompt_state.haul_prompt_step = "search_max_station_distance_ls"
        next_default = resolved_default("max_station_distance_ls")
        return HaulSearchPromptTransition(
            log_lines=(
                f"  Min. landing pad: [cyan]{_search_choice_label(parsed, _LANDING_PAD_LABELS)}[/]",
                f"[dim]Max. station distance? (Ls, Enter = {escape(next_default)})[/]",
            ),
            ui_state=HaulPromptUiState(
                placeholder=f"max station distance ls (Enter = {next_default})...",
                value=_search_prefill_value_from_state(prompt_state, "max_station_distance_ls")
                or next_default,
            ),
        )

    if prompt_state.haul_prompt_step == "search_use_surface_stations":
        default_value = resolved_default("use_surface_stations")
        parsed = _parse_surface_stations(value, default=default_value)
        if parsed is None:
            return HaulSearchPromptTransition(
                log_lines=(
                    "[red]Use surface stations must be no, yes-with-odyssey, or yes-exclude-odyssey.[/]",
                ),
            )
        prompt_state.haul_search_params["use_surface_stations"] = parsed
        prompt_state.haul_prompt_step = "search_min_supply"
        next_default = resolved_default("min_supply")
        return HaulSearchPromptTransition(
            log_lines=(
                f"  Use surface stations: [cyan]{escape(_search_choice_label(parsed, _SURFACE_STATION_LABELS))}[/]",
                f"[dim]Min. supply? (Enter = {escape(next_default)})[/]",
            ),
            ui_state=HaulPromptUiState(
                placeholder=f"min supply (Enter = {next_default})...",
                value=_search_prefill_value_from_state(prompt_state, "min_supply") or next_default,
            ),
        )

    if prompt_state.haul_prompt_step == "search_include_round_trips":
        parsed = _parse_yes_no(
            value,
            default=resolved_default("include_round_trips").strip().lower() == "true",
        )
        if parsed is None:
            return HaulSearchPromptTransition(
                log_lines=(f"[red]{escape(error_text.render(app._config, 'confirm_yes_no'))}[/]",),
            )
        prompt_state.haul_search_params["include_round_trips"] = "true" if parsed else "false"
        prompt_state.haul_prompt_step = "search_order_by"
        default_value = resolved_default("order_by")
        label_value = _search_choice_label(default_value, _ORDER_BY_LABELS)
        return HaulSearchPromptTransition(
            log_lines=(
                f"  Include round trips: [cyan]{'yes' if parsed else 'no'}[/]",
                f"[dim]Order by? (Enter = {escape(label_value)})[/]",
            ),
            ui_state=HaulPromptUiState(
                placeholder=f"order by (Enter = {label_value})...",
                value=_search_prefill_value_from_state(prompt_state, "order_by") or default_value,
            ),
        )

    if prompt_state.haul_prompt_step == "search_order_by":
        default_value = resolved_default("order_by")
        parsed = _parse_order_by(value, default=default_value)
        if parsed is None:
            return HaulSearchPromptTransition(
                log_lines=(
                    "[red]Order by must be best-profit/hour, best-profit, last-update, route-distance, or distance.[/]",
                ),
            )
        prompt_state.haul_search_params["order_by"] = parsed
        prompt_state.haul_prompt_step = ""
        prompt_state.haul_prompt_mode = ""
        prompt_state.haul_prompt_defaults = {}
        prompt_state.haul_search_prompt_defaults = {}
        query_params = dict(prompt_state.haul_search_params)
        prompt_state.haul_search_params = {}
        system_name = query_params.pop("near_system", "").strip()
        return HaulSearchPromptTransition(
            log_lines=(
                f"  Order by: [cyan]{escape(_search_choice_label(parsed, _ORDER_BY_LABELS))}[/]",
            ),
            ui_state=HaulPromptUiState(placeholder=default_placeholder),
            launch_haul_search=bool(system_name),
            system_name=system_name,
            query_params=query_params,
            skip_delay=prompt_state.haul_prompt_skip_delay,
            raw_command=prompt_state.haul_prompt_raw_command,
        )

    return HaulSearchPromptTransition()


def parse_optional_nonnegative_float(
    app: PromptHost,
    raw: str,
    *,
    default: float,
    label: str,
) -> float | None:
    value = raw.strip()
    if not value:
        return default
    try:
        parsed = float(value)
    except ValueError:
        app._log(
            f"[red]{escape(error_text.render(app._config, 'number_required', label=label))}[/]"
        )
        return None
    if parsed < 0:
        app._log(
            f"[red]{escape(error_text.render(app._config, 'nonnegative_required', label=label))}[/]"
        )
        return None
    return parsed


def parse_optional_nonnegative_int(
    app: PromptHost,
    raw: str,
    *,
    default: str,
    label: str,
) -> str | None:
    value = raw.strip()
    if not value:
        return default
    try:
        parsed = int(value)
    except ValueError:
        app._log(
            f"[red]{escape(error_text.render(app._config, 'number_required', label=label))}[/]"
        )
        return None
    if parsed < 0:
        app._log(
            f"[red]{escape(error_text.render(app._config, 'nonnegative_required', label=label))}[/]"
        )
        return None
    return str(parsed)
