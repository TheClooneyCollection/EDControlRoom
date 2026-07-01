from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import json
from pathlib import Path
import sys
import tomllib
import yaml

from edap.timing import (
    TimingChannelConfig,
    TimingConfig,
    VALID_TIMING_DISTRIBUTIONS,
)


DEFAULT_CONFIG_PATH = Path("config.toml")
EXAMPLE_CONFIG_PATH = Path("config.example.toml")
DEFAULT_PATHS_CONFIG_PATH = Path(__file__).resolve().parent.parent / "defaults" / "paths.toml"
DEFAULT_RUNTIME_CONFIG_PATH = Path(__file__).resolve().parent.parent / "defaults" / "runtime.toml"
DEFAULT_CONTROLS_CONFIG_PATH = Path(__file__).resolve().parent.parent / "defaults" / "controls.toml"
DEFAULT_SCREEN_CONFIG_PATH = Path(__file__).resolve().parent.parent / "defaults" / "screen.toml"
DEFAULT_CONTROL_ROOM_CONFIG_PATH = Path(__file__).resolve().parent.parent / "defaults" / "control_room.toml"
DEFAULT_TIMING_CONFIG_PATH = Path(__file__).resolve().parent.parent / "defaults" / "timing.toml"
DEFAULT_TTS_CONFIG_PATH = Path(__file__).resolve().parent.parent / "defaults" / "tts.toml"
DEFAULT_ERROR_MESSAGES_CONFIG_PATH = Path(__file__).resolve().parent.parent / "defaults" / "error_messages.yaml"
DEFAULT_MESSAGES_CONFIG_PATH = Path(__file__).resolve().parent.parent / "defaults" / "messages.yaml"

VALID_PLATFORMS = {"linux", "macos", "windows"}
VALID_CAPTURE_MODES = {"fullscreen", "region"}
VALID_TTS_TITLE_MODES = {"commander", "custom", "commander_name"}
VALID_MARKET_BUY_HOLD_SEGMENT_FUNCTIONS = {"flat", "linear", "log"}


def default_runtime_platform() -> str:
    if sys.platform == "darwin":
        return "macos"
    if sys.platform.startswith("linux"):
        return "linux"
    if sys.platform.startswith("win"):
        return "windows"
    raise ConfigError(
        "Config value `runtime.platform` must be set explicitly on this host. "
        "Supported runtime values are: linux, macos, windows."
    )


@dataclass(frozen=True)
class PathsConfig:
    journal_dir: Path | None
    bindings_file: Path | None


@dataclass(frozen=True)
class MarketBuyHoldSegmentConfig:
    start: int
    function: str
    hold_seconds: float = 0.0
    seconds_per_ton: float = 0.01
    base_seconds: float = 0.0
    multiplier: float = 1.0


@dataclass(frozen=True)
class ControlsConfig:
    start_hotkey: str
    stop_hotkey: str
    scanner_mode: str
    minimum_action_hold_seconds: float
    continuous_action_hold_seconds: float
    step_delay_seconds: float
    galaxy_map_settle_seconds: float
    dock_supercruise_exit_settle_seconds: float
    haul_dock_timeout_seconds: float
    undock_timeout_seconds: float
    undock_no_track_timeout_seconds: float
    mass_lock_boost_delay_seconds: float
    market_nav_delay_seconds: float
    market_trade_max_attempts: int
    market_buy_max_hold_seconds: float
    market_buy_hold_segments: tuple[MarketBuyHoldSegmentConfig, ...]
    market_sell_quantity_restore_taps: int
    market_sell_quantity_restore_tap_delay_seconds: float
    market_critical_level_multiplier: float
    haul_post_sell_settle_seconds: float
    haul_two_way_auto_hyperspace_engage: bool
    haul_two_way_open_nav_panel_after_hyperspace_arrival: bool
    haul_two_way_nav_panel_open_delay_seconds: float


@dataclass(frozen=True)
class HaulRoutineDefaults:
    market_buy_hold_segments: tuple[MarketBuyHoldSegmentConfig, ...]
    market_sell_quantity_restore_taps: int
    market_sell_quantity_restore_tap_delay_seconds: float
    dock_timeout_seconds: float
    undock_timeout_seconds: float
    undock_no_track_timeout_seconds: float
    galaxy_map_settle_seconds: float
    dock_supercruise_exit_settle_seconds: float
    mass_lock_boost_delay_seconds: float
    haul_post_sell_settle_seconds: float
    haul_two_way_auto_hyperspace_engage: bool
    haul_two_way_open_nav_panel_after_hyperspace_arrival: bool
    haul_two_way_nav_panel_open_delay_seconds: float
    market_critical_level_multiplier: float


@dataclass(frozen=True)
class ScreenConfig:
    resolution_width: int
    resolution_height: int
    scale: float
    capture_debug_path: Path | None
    capture: "CaptureConfig"


@dataclass(frozen=True)
class CaptureRegionConfig:
    left: float
    top: float
    right: float
    bottom: float


@dataclass(frozen=True)
class CaptureConfig:
    mode: str
    base_region: CaptureRegionConfig
    regions: dict[str, CaptureRegionConfig]


@dataclass(frozen=True)
class RuntimeConfig:
    platform: str
    debug: bool


@dataclass(frozen=True)
class ControlRoomConfig:
    state_file: Path
    history_limit: int
    activity_log_max_lines: int
    command_delay_seconds: float
    status_refresh_seconds: float = 2.0
    check_for_updates: bool = True
    home_system: str = ""
    clear_session_on_launch: bool = False


@dataclass(frozen=True)
class TTSConfig:
    enabled: bool = True
    title_mode: str = "commander"
    title: str = "commander"
    disabled_messages: tuple[str, ...] = ()
    phrases: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ErrorMessagesConfig:
    templates: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class MessagesConfig:
    templates: dict[str, str] = field(default_factory=dict)


def default_error_messages_config() -> ErrorMessagesConfig:
    return ErrorMessagesConfig(templates=_message_template_dict(_load_default_error_messages_table(), "templates"))


def default_messages_config() -> MessagesConfig:
    return MessagesConfig(templates=_string_dict(_load_default_messages_table(), "templates"))


@dataclass(frozen=True)
class AppConfig:
    paths: PathsConfig
    controls: ControlsConfig
    screen: ScreenConfig
    runtime: RuntimeConfig
    timing: "TimingConfig"
    control_room: ControlRoomConfig
    tts: TTSConfig = field(default_factory=TTSConfig)
    messages: MessagesConfig = field(default_factory=default_messages_config)
    error_messages: ErrorMessagesConfig = field(default_factory=default_error_messages_config)


class ConfigError(ValueError):
    """Raised when config parsing or validation fails."""


def _load_default_toml_section(path: Path, section: str, label: str) -> dict[str, object]:
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    if not isinstance(raw, dict):
        raise ConfigError(f"Default {label} config root must be a TOML table.")
    value = raw.get(section, {})
    if not isinstance(value, dict):
        raise ConfigError(f"Default {label} config section `{section}` must be a table.")
    return value


@lru_cache(maxsize=1)
def _load_default_paths_table() -> dict[str, object]:
    return _load_default_toml_section(DEFAULT_PATHS_CONFIG_PATH, "paths", "paths")


@lru_cache(maxsize=1)
def _load_default_runtime_table() -> dict[str, object]:
    return _load_default_toml_section(DEFAULT_RUNTIME_CONFIG_PATH, "runtime", "runtime")


@lru_cache(maxsize=1)
def _load_default_controls_table() -> dict[str, object]:
    return _load_default_toml_section(DEFAULT_CONTROLS_CONFIG_PATH, "controls", "controls")


@lru_cache(maxsize=1)
def _load_default_screen_table() -> dict[str, object]:
    return _load_default_toml_section(DEFAULT_SCREEN_CONFIG_PATH, "screen", "screen")


@lru_cache(maxsize=1)
def _load_default_control_room_table() -> dict[str, object]:
    return _load_default_toml_section(DEFAULT_CONTROL_ROOM_CONFIG_PATH, "control_room", "control-room")


@lru_cache(maxsize=1)
def _load_default_tts_table() -> dict[str, object]:
    return _load_default_toml_section(DEFAULT_TTS_CONFIG_PATH, "tts", "TTS")


@lru_cache(maxsize=1)
def _load_default_timing_table() -> dict[str, object]:
    return _load_default_toml_section(DEFAULT_TIMING_CONFIG_PATH, "timing", "timing")


@lru_cache(maxsize=1)
def _load_default_error_messages_table() -> dict[str, object]:
    raw = _load_yaml_table(DEFAULT_ERROR_MESSAGES_CONFIG_PATH)
    if not isinstance(raw, dict):
        raise ConfigError("Default error-messages config root must be a YAML mapping.")
    value = raw.get("error_messages", {})
    if not isinstance(value, dict):
        raise ConfigError("Default error-messages config section `error_messages` must be a mapping.")
    return value


@lru_cache(maxsize=1)
def _load_default_messages_table() -> dict[str, object]:
    raw = _load_yaml_table(DEFAULT_MESSAGES_CONFIG_PATH)
    if not isinstance(raw, dict):
        raise ConfigError("Default messages config root must be a YAML mapping.")
    value = raw.get("messages", {})
    if not isinstance(value, dict):
        raise ConfigError("Default messages config section `messages` must be a mapping.")
    return value


def _load_yaml_table(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ConfigError(f"Default YAML config root must be a mapping: {path}")
    return raw


def _optional_path(value: object) -> Path | None:
    if not value:
        return None
    return Path(str(value)).expanduser()


def _require_table(raw: dict[str, object], key: str) -> dict[str, object]:
    value = raw.get(key, {})
    if not isinstance(value, dict):
        raise ConfigError(f"Config section `{key}` must be a table.")
    return value


def _optional_table(raw: dict[str, object], key: str) -> dict[str, object]:
    value = raw.get(key, {})
    if not isinstance(value, dict):
        raise ConfigError(f"Config section `{key}` must be a table.")
    return value


def _merge_tables(defaults: dict[str, object], overrides: dict[str, object]) -> dict[str, object]:
    merged = dict(defaults)
    for key, value in overrides.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = _merge_tables(current, value)
            continue
        merged[key] = value
    return merged


def _default_app_config_table() -> dict[str, object]:
    return {
        "paths": _load_default_paths_table(),
        "runtime": _load_default_runtime_table(),
        "controls": _load_default_controls_table(),
        "screen": _load_default_screen_table(),
        "control_room": _load_default_control_room_table(),
        "timing": _load_default_timing_table(),
        "tts": _load_default_tts_table(),
    }


def _with_default_app_config(raw: dict[str, object]) -> dict[str, object]:
    return _merge_tables(_default_app_config_table(), raw)


def default_haul_routine_defaults() -> HaulRoutineDefaults:
    controls = _load_default_controls_table()
    controls_flat = _flatten_table(controls)
    controls_market = _optional_table(controls, "market")
    return HaulRoutineDefaults(
        market_buy_hold_segments=_market_buy_hold_segments(controls_market, "buy_hold_segments"),
        market_sell_quantity_restore_taps=_integer(controls_flat, "market.sell_quantity_restore_taps", 0),
        market_sell_quantity_restore_tap_delay_seconds=_float(
            controls_flat,
            "market.sell_quantity_restore_tap_delay_seconds",
            0.0,
        ),
        dock_timeout_seconds=_float(controls_flat, "haul.dock_timeout_seconds", 0.0),
        undock_timeout_seconds=_float(controls_flat, "undock.timeout_seconds", 0.0),
        undock_no_track_timeout_seconds=_float(controls_flat, "undock.no_track_timeout_seconds", 0.0),
        galaxy_map_settle_seconds=_float(controls_flat, "galaxy_map.settle_seconds", 0.0),
        dock_supercruise_exit_settle_seconds=_float(controls_flat, "dock.supercruise_exit_settle_seconds", 0.0),
        mass_lock_boost_delay_seconds=_float(controls_flat, "mass_lock.boost_delay_seconds", 0.0),
        haul_post_sell_settle_seconds=_float(controls_flat, "haul.post_sell_settle_seconds", 0.0),
        haul_two_way_auto_hyperspace_engage=_boolean(
            controls_flat,
            "haul.two_way.auto_hyperspace_engage",
            False,
        ),
        haul_two_way_open_nav_panel_after_hyperspace_arrival=_boolean(
            controls_flat,
            "haul.two_way.open_nav_panel_after_hyperspace_arrival",
            False,
        ),
        haul_two_way_nav_panel_open_delay_seconds=_float(
            controls_flat,
            "haul.two_way.nav_panel_open_delay_seconds",
            0.0,
        ),
        market_critical_level_multiplier=_float(controls_flat, "market.critical_level_multiplier", 0.0),
    )


def _lookup_value(raw: dict[str, object], key: str, aliases: tuple[str, ...] = ()) -> object | None:
    if key in raw:
        return raw[key]
    for alias in aliases:
        if alias in raw:
            return raw[alias]
    return None


def _flatten_table(raw: dict[str, object], *, prefix: str = "") -> dict[str, object]:
    flattened: dict[str, object] = {}
    for key, value in raw.items():
        dotted_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flattened.update(_flatten_table(value, prefix=dotted_key))
            continue
        flattened[dotted_key] = value
    return flattened


def _string(raw: dict[str, object], key: str, default: str, *, aliases: tuple[str, ...] = ()) -> str:
    value = _lookup_value(raw, key, aliases)
    if value is None:
        value = default
    if not isinstance(value, str):
        raise ConfigError(f"Config value `{key}` must be a string.")
    return value


def _integer(raw: dict[str, object], key: str, default: int, *, aliases: tuple[str, ...] = ()) -> int:
    value = _lookup_value(raw, key, aliases)
    if value is None:
        value = default
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"Config value `{key}` must be an integer.")
    return value


def _float(raw: dict[str, object], key: str, default: float, *, aliases: tuple[str, ...] = ()) -> float:
    value = _lookup_value(raw, key, aliases)
    if value is None:
        value = default
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"Config value `{key}` must be a number.")
    return float(value)


def _boolean(raw: dict[str, object], key: str, default: bool, *, aliases: tuple[str, ...] = ()) -> bool:
    value = _lookup_value(raw, key, aliases)
    if value is None:
        value = default
    if not isinstance(value, bool):
        raise ConfigError(f"Config value `{key}` must be true or false.")
    return value


def _string_list(raw: dict[str, object], key: str) -> tuple[str, ...]:
    value = raw.get(key, [])
    if not isinstance(value, list):
        raise ConfigError(f"Config value `{key}` must be a list of strings.")
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise ConfigError(f"Config value `{key}[{index}]` must be a string.")
        result.append(item)
    return tuple(result)


def _string_dict(raw: dict[str, object], key: str) -> dict[str, str]:
    value = raw.get(key, {})
    if not isinstance(value, dict):
        raise ConfigError(f"Config section `{key}` must be a table.")
    result: dict[str, str] = {}
    for sub_key, sub_value in value.items():
        if not isinstance(sub_key, str) or not isinstance(sub_value, str):
            raise ConfigError(f"Config section `{key}` must contain only string values.")
        result[sub_key] = sub_value
    return result


def _message_template_dict(raw: dict[str, object], key: str) -> dict[str, str]:
    value = raw.get(key, {})
    if not isinstance(value, dict):
        raise ConfigError(f"Config section `{key}` must be a table.")
    result: dict[str, str] = {}
    for sub_key, sub_value in value.items():
        if not isinstance(sub_key, str):
            raise ConfigError(f"Config section `{key}` must contain only string keys.")
        if isinstance(sub_value, str):
            result[sub_key] = sub_value
            continue
        if not isinstance(sub_value, dict):
            raise ConfigError(
                f"Config section `{key}.{sub_key}` must be a string or a table with string fields."
            )
        for field_name, field_value in sub_value.items():
            if field_name not in {"message", "suggestion"} or not isinstance(field_value, str):
                raise ConfigError(
                    f"Config section `{key}.{sub_key}` must contain only string `message`/`suggestion` fields."
                )
            result[f"{sub_key}_{field_name}"] = field_value
    return result


def _validate_path_shape(path: Path | None, *, key: str, should_be_dir: bool) -> None:
    if path is None or not path.exists():
        return
    if should_be_dir and not path.is_dir():
        raise ConfigError(f"Config path `{key}` must point to a directory: {path}")
    if not should_be_dir and not path.is_file():
        raise ConfigError(f"Config path `{key}` must point to a file: {path}")


def _capture_region(
    raw: dict[str, object],
    defaults: tuple[float, float, float, float],
) -> CaptureRegionConfig:
    return CaptureRegionConfig(
        left=_float(raw, "left", defaults[0]),
        top=_float(raw, "top", defaults[1]),
        right=_float(raw, "right", defaults[2]),
        bottom=_float(raw, "bottom", defaults[3]),
    )


def _market_buy_hold_segments(raw: dict[str, object], key: str) -> tuple[MarketBuyHoldSegmentConfig, ...]:
    value = raw.get(key)
    if value is None:
        return (
            MarketBuyHoldSegmentConfig(start=0, function="flat", hold_seconds=3.0),
            MarketBuyHoldSegmentConfig(start=100, function="flat", hold_seconds=5.0),
            MarketBuyHoldSegmentConfig(start=301, function="log", base_seconds=-12.5627, multiplier=3.0756),
        )
    if not isinstance(value, list):
        raise ConfigError(f"Config section `{key}` must be an array of tables.")

    segments: list[MarketBuyHoldSegmentConfig] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ConfigError(f"Config section `{key}[{index}]` must be a table.")
        start = _integer(item, "start", 0)
        function = _string(item, "function", "")
        segments.append(
            MarketBuyHoldSegmentConfig(
                start=start,
                function=function,
                hold_seconds=_float(item, "hold_seconds", 0.0),
                seconds_per_ton=_float(item, "seconds_per_ton", 0.01),
                base_seconds=_float(item, "base_seconds", 0.0),
                multiplier=_float(item, "multiplier", 1.0),
            )
        )
    return tuple(segments)


def _validate_capture_region(region: CaptureRegionConfig, *, key: str) -> None:
    for name, value in (
        ("left", region.left),
        ("top", region.top),
        ("right", region.right),
        ("bottom", region.bottom),
    ):
        if value < 0 or value > 1:
            raise ConfigError(f"Config value `{key}.{name}` must be between 0.0 and 1.0.")

    if region.left >= region.right:
        raise ConfigError(f"Config region `{key}` must have left < right.")
    if region.top >= region.bottom:
            raise ConfigError(f"Config region `{key}` must have top < bottom.")


def _timing_channel(
    raw: dict[str, object],
    defaults: dict[str, object],
) -> TimingChannelConfig:
    return TimingChannelConfig(
        sigma=_float(raw, "sigma", _float(defaults, "sigma", 0.0)),
        min_factor=_float(raw, "min_factor", _float(defaults, "min_factor", 1.0)),
        max_factor=_float(raw, "max_factor", _float(defaults, "max_factor", 1.0)),
        min_seconds=_float(raw, "min_seconds", _float(defaults, "min_seconds", 0.0)),
    )


def validate_config(config: AppConfig) -> AppConfig:
    if not config.controls.start_hotkey.strip():
        raise ConfigError("Config value `controls.start_hotkey` cannot be empty.")
    if not config.controls.stop_hotkey.strip():
        raise ConfigError("Config value `controls.stop_hotkey` cannot be empty.")
    if config.controls.minimum_action_hold_seconds <= 0:
        raise ConfigError("Config value `controls.minimum_action_hold_seconds` must be greater than 0.")
    if config.controls.continuous_action_hold_seconds <= 0:
        raise ConfigError("Config value `controls.continuous_action_hold_seconds` must be greater than 0.")
    if config.controls.continuous_action_hold_seconds < config.controls.minimum_action_hold_seconds:
        raise ConfigError(
            "Config value `controls.continuous_action_hold_seconds` must be greater than or equal to "
            "`controls.minimum_action_hold_seconds`."
        )
    if config.controls.step_delay_seconds < 0:
        raise ConfigError("Config value `controls.step_delay_seconds` must be non-negative.")
    if config.controls.galaxy_map_settle_seconds < 0:
        raise ConfigError("Config value `controls.galaxy_map_settle_seconds` must be non-negative.")
    if config.controls.dock_supercruise_exit_settle_seconds < 0:
        raise ConfigError("Config value `controls.dock_supercruise_exit_settle_seconds` must be non-negative.")
    if config.controls.haul_dock_timeout_seconds < 0:
        raise ConfigError("Config value `controls.haul_dock_timeout_seconds` must be non-negative.")
    if config.controls.undock_timeout_seconds < 0:
        raise ConfigError("Config value `controls.undock_timeout_seconds` must be non-negative.")
    if config.controls.undock_no_track_timeout_seconds < 0:
        raise ConfigError("Config value `controls.undock_no_track_timeout_seconds` must be non-negative.")
    if config.controls.mass_lock_boost_delay_seconds < 0:
        raise ConfigError("Config value `controls.mass_lock_boost_delay_seconds` must be non-negative.")
    if config.controls.market_nav_delay_seconds < 0:
        raise ConfigError("Config value `controls.market_nav_delay_seconds` must be non-negative.")
    if config.controls.market_trade_max_attempts < 1:
        raise ConfigError("Config value `controls.market_trade_max_attempts` must be at least 1.")
    if config.controls.market_buy_max_hold_seconds <= 0:
        raise ConfigError("Config value `controls.market_buy_max_hold_seconds` must be greater than 0.")
    if not config.controls.market_buy_hold_segments:
        raise ConfigError("Config section `controls.market.buy_hold_segments` must contain at least one segment.")
    if config.controls.market_buy_hold_segments[0].start != 0:
        raise ConfigError("Config section `controls.market.buy_hold_segments` must start at 0 tons.")
    last_start = -1
    for index, segment in enumerate(config.controls.market_buy_hold_segments):
        if segment.start < 0:
            raise ConfigError(f"Config value `controls.market.buy_hold_segments[{index}].start` must be non-negative.")
        if segment.start <= last_start:
            raise ConfigError(
                "Config section `controls.market.buy_hold_segments` must be in strictly increasing `start` order."
            )
        last_start = segment.start
        if segment.function not in VALID_MARKET_BUY_HOLD_SEGMENT_FUNCTIONS:
            supported = ", ".join(sorted(VALID_MARKET_BUY_HOLD_SEGMENT_FUNCTIONS))
            raise ConfigError(
                f"Config value `controls.market.buy_hold_segments[{index}].function` must be one of: {supported}."
            )
        if segment.function == "flat" and segment.hold_seconds < 0:
            raise ConfigError(
                f"Config value `controls.market.buy_hold_segments[{index}].hold_seconds` must be non-negative."
            )
        if segment.function == "linear" and segment.seconds_per_ton <= 0:
            raise ConfigError(
                f"Config value `controls.market.buy_hold_segments[{index}].seconds_per_ton` must be greater than 0."
            )
        if segment.function == "log" and segment.multiplier <= 0:
            raise ConfigError(
                f"Config value `controls.market.buy_hold_segments[{index}].multiplier` must be greater than 0."
            )
    if config.controls.market_sell_quantity_restore_taps < 1:
        raise ConfigError("Config value `controls.market_sell_quantity_restore_taps` must be at least 1.")
    if config.controls.market_sell_quantity_restore_tap_delay_seconds < 0:
        raise ConfigError(
            "Config value `controls.market_sell_quantity_restore_tap_delay_seconds` must be non-negative."
        )
    if config.controls.market_critical_level_multiplier <= 0:
        raise ConfigError("Config value `controls.market_critical_level_multiplier` must be greater than 0.")
    if config.controls.haul_post_sell_settle_seconds < 0:
        raise ConfigError("Config value `controls.haul_post_sell_settle_seconds` must be non-negative.")
    if config.controls.haul_two_way_nav_panel_open_delay_seconds < 0:
        raise ConfigError("Config value `controls.haul_two_way_nav_panel_open_delay_seconds` must be non-negative.")
    if config.screen.resolution_width <= 0:
        raise ConfigError("Config value `screen.resolution_width` must be greater than 0.")
    if config.screen.resolution_height <= 0:
        raise ConfigError("Config value `screen.resolution_height` must be greater than 0.")
    if config.screen.scale <= 0:
        raise ConfigError("Config value `screen.scale` must be greater than 0.")
    if config.screen.capture.mode not in VALID_CAPTURE_MODES:
        supported = ", ".join(sorted(VALID_CAPTURE_MODES))
        raise ConfigError(f"Config value `screen.capture.mode` must be one of: {supported}.")
    if config.runtime.platform.lower() not in VALID_PLATFORMS:
        supported = ", ".join(sorted(VALID_PLATFORMS))
        raise ConfigError(
            f"Config value `runtime.platform` must be one of: {supported}."
        )
    if config.timing.distribution not in VALID_TIMING_DISTRIBUTIONS:
        supported = ", ".join(sorted(VALID_TIMING_DISTRIBUTIONS))
        raise ConfigError(f"Config value `timing.distribution` must be one of: {supported}.")
    for name, channel in (
        ("delay", config.timing.delay),
        ("hold", config.timing.hold),
        ("typing", config.timing.typing),
    ):
        if channel.sigma < 0:
            raise ConfigError(f"Config value `timing.{name}.sigma` must be non-negative.")
        if channel.min_factor <= 0:
            raise ConfigError(f"Config value `timing.{name}.min_factor` must be greater than 0.")
        if channel.max_factor < channel.min_factor:
            raise ConfigError(
                f"Config value `timing.{name}.max_factor` must be greater than or equal to `timing.{name}.min_factor`."
            )
        if channel.min_seconds < 0:
            raise ConfigError(f"Config value `timing.{name}.min_seconds` must be non-negative.")
    if config.control_room.history_limit <= 0:
        raise ConfigError("Config value `control_room.history_limit` must be greater than 0.")
    if config.control_room.activity_log_max_lines <= 0:
        raise ConfigError("Config value `control_room.activity_log_max_lines` must be greater than 0.")
    if config.control_room.command_delay_seconds < 0:
        raise ConfigError("Config value `control_room.command_delay_seconds` must be non-negative.")
    if config.control_room.status_refresh_seconds < 0:
        raise ConfigError("Config value `control_room.status_refresh_seconds` must be non-negative.")
    if config.tts.title_mode not in VALID_TTS_TITLE_MODES:
        supported = ", ".join(sorted(VALID_TTS_TITLE_MODES))
        raise ConfigError(f"Config value `tts.title_mode` must be one of: {supported}.")
    if config.tts.title_mode == "custom" and not config.tts.title.strip():
        raise ConfigError("Config value `tts.title` cannot be empty when `tts.title_mode` is `custom`.")

    _validate_path_shape(config.paths.journal_dir, key="paths.journal_dir", should_be_dir=True)
    _validate_path_shape(config.paths.bindings_file, key="paths.bindings_file", should_be_dir=False)
    if config.screen.capture_debug_path and config.screen.capture_debug_path.exists():
        if config.screen.capture_debug_path.is_dir():
            raise ConfigError(
                "Config value `screen.capture_debug_path` must point to a file, not a directory."
            )
    _validate_capture_region(config.screen.capture.base_region, key="screen.capture.base_region")
    for name, region in config.screen.capture.regions.items():
        if not name.strip():
            raise ConfigError("Config section `screen.capture.regions` cannot contain an empty name.")
        _validate_capture_region(region, key=f"screen.capture.regions.{name}")

    return config


def save_home_system(path: Path | str, system_name: str) -> Path:
    config_path = Path(path)
    home_system = system_name.strip()
    if not home_system:
        raise ConfigError("Home system cannot be empty.")

    if not config_path.exists():
        config_path.write_text(_minimal_config_text(home_system), encoding="utf-8")
        return config_path

    existing = config_path.read_text(encoding="utf-8")
    updated = _upsert_toml_string(existing, section="control_room", key="home_system", value=home_system)
    config_path.write_text(updated, encoding="utf-8")
    return config_path


def _minimal_config_text(home_system: str) -> str:
    return "\n".join((
        "[paths]",
        "",
        "[controls]",
        "",
        "[screen]",
        "",
        "[runtime]",
        "",
        "[control_room]",
        f"home_system = {_toml_basic_string(home_system)}",
        "",
    ))


def _upsert_toml_string(content: str, *, section: str, key: str, value: str) -> str:
    lines = content.splitlines(keepends=True)
    section_header = f"[{section}]"
    key_prefix = f"{key} = "
    section_start: int | None = None
    section_end = len(lines)

    for index, line in enumerate(lines):
        stripped = line.strip()
        if not (stripped.startswith("[") and stripped.endswith("]")):
            continue
        if stripped == section_header:
            section_start = index
            continue
        if section_start is not None:
            section_end = index
            break

    rendered = f"{key_prefix}{_toml_basic_string(value)}\n"

    if section_start is None:
        suffix = "" if not content or content.endswith("\n") else "\n"
        spacer = "\n" if content.strip() else ""
        return f"{content}{suffix}{spacer}[{section}]\n{rendered}"

    for index in range(section_start + 1, section_end):
        if lines[index].lstrip().startswith(f"{key} ="):
            lines[index] = rendered
            return "".join(lines)

    insert_at = section_end
    while insert_at > section_start + 1 and not lines[insert_at - 1].strip():
        insert_at -= 1
    lines.insert(insert_at, rendered)
    return "".join(lines)


def _toml_basic_string(value: str) -> str:
    return json.dumps(value)


def load_config(path: Path | str = DEFAULT_CONFIG_PATH) -> AppConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)

    if not isinstance(raw, dict):
        raise ConfigError("Config root must be a TOML table.")

    raw = _with_default_app_config(raw)

    paths = _require_table(raw, "paths")
    controls = _require_table(raw, "controls")
    controls_market = _optional_table(controls, "market")
    controls_flat = _flatten_table(controls)
    screen = _require_table(raw, "screen")
    screen_capture = _optional_table(screen, "capture")
    screen_capture_regions = _optional_table(screen_capture, "regions")
    runtime = _require_table(raw, "runtime")
    control_room = _optional_table(raw, "control_room")
    tts = _optional_table(raw, "tts")
    messages = _optional_table(raw, "messages")
    error_messages = _optional_table(raw, "error_messages")
    timing = _optional_table(raw, "timing")
    timing_delay = _optional_table(timing, "delay")
    timing_hold = _optional_table(timing, "hold")
    timing_typing = _optional_table(timing, "typing")
    default_controls = _load_default_controls_table()
    default_controls_flat = _flatten_table(default_controls)
    default_screen = _load_default_screen_table()
    default_screen_capture = _optional_table(default_screen, "capture")
    default_runtime = _load_default_runtime_table()
    default_tts = _load_default_tts_table()
    default_control_room = _load_default_control_room_table()
    default_timing = _load_default_timing_table()
    default_timing_delay = _optional_table(default_timing, "delay")
    default_timing_hold = _optional_table(default_timing, "hold")
    default_timing_typing = _optional_table(default_timing, "typing")
    default_messages = _load_default_messages_table()
    default_error_messages = _load_default_error_messages_table()

    capture_regions: dict[str, CaptureRegionConfig] = {
        "center": CaptureRegionConfig(
            left=1 / 3,
            top=1 / 3,
            right=2 / 3,
            bottom=2 / 3,
        ),
        "compass": CaptureRegionConfig(
            left=5 / 16,
            top=5 / 8,
            right=2 / 4,
            bottom=15 / 16,
        ),
    }
    for name, region_raw in screen_capture_regions.items():
        if not isinstance(name, str) or not isinstance(region_raw, dict):
            raise ConfigError("Config section `screen.capture.regions` must contain named tables.")
        capture_regions[name] = _capture_region(
            region_raw,
            (0.0, 0.0, 1.0, 1.0),
        )

    config = AppConfig(
        paths=PathsConfig(
            journal_dir=_optional_path(paths.get("journal_dir")),
            bindings_file=_optional_path(paths.get("bindings_file")),
        ),
        controls=ControlsConfig(
            start_hotkey=_string(controls_flat, "start_hotkey", _string(default_controls_flat, "start_hotkey", "")),
            stop_hotkey=_string(controls_flat, "stop_hotkey", _string(default_controls_flat, "stop_hotkey", "")),
            scanner_mode=_string(controls_flat, "scanner_mode", _string(default_controls_flat, "scanner_mode", "")),
            minimum_action_hold_seconds=_float(
                controls_flat,
                "minimum_action_hold_seconds",
                _float(default_controls_flat, "minimum_action_hold_seconds", 0.0),
                aliases=("hold.minimum_action_seconds",),
            ),
            continuous_action_hold_seconds=_float(
                controls_flat,
                "continuous_action_hold_seconds",
                _float(default_controls_flat, "continuous_action_hold_seconds", 0.0),
                aliases=("hold.continuous_action_seconds",),
            ),
            step_delay_seconds=_float(
                controls_flat,
                "step_delay_seconds",
                _float(default_controls_flat, "step_delay_seconds", 0.0),
                aliases=("sequence.step_delay_seconds",),
            ),
            galaxy_map_settle_seconds=_float(
                controls_flat,
                "galaxy_map_settle_seconds",
                _float(default_controls_flat, "galaxy_map_settle_seconds", 0.0),
                aliases=("galaxy_map.settle_seconds",),
            ),
            dock_supercruise_exit_settle_seconds=_float(
                controls_flat,
                "dock_supercruise_exit_settle_seconds",
                _float(default_controls_flat, "dock_supercruise_exit_settle_seconds", 0.0),
                aliases=("dock.supercruise_exit_settle_seconds",),
            ),
            haul_dock_timeout_seconds=_float(
                controls_flat,
                "haul_dock_timeout_seconds",
                _float(default_controls_flat, "haul_dock_timeout_seconds", 0.0),
                aliases=("haul.dock_timeout_seconds",),
            ),
            undock_timeout_seconds=_float(
                controls_flat,
                "undock_timeout_seconds",
                _float(default_controls_flat, "undock_timeout_seconds", 0.0),
                aliases=("undock.timeout_seconds",),
            ),
            undock_no_track_timeout_seconds=_float(
                controls_flat,
                "undock_no_track_timeout_seconds",
                _float(default_controls_flat, "undock_no_track_timeout_seconds", 0.0),
                aliases=("undock.no_track_timeout_seconds",),
            ),
            mass_lock_boost_delay_seconds=_float(
                controls_flat,
                "mass_lock_boost_delay_seconds",
                _float(default_controls_flat, "mass_lock_boost_delay_seconds", 0.0),
                aliases=("mass_lock.boost_delay_seconds",),
            ),
            market_nav_delay_seconds=_float(
                controls_flat,
                "market_nav_delay_seconds",
                _float(default_controls_flat, "market_nav_delay_seconds", 0.0),
                aliases=("market.nav_delay_seconds",),
            ),
            market_trade_max_attempts=_integer(
                controls_flat,
                "market_trade_max_attempts",
                _integer(default_controls_flat, "market_trade_max_attempts", 0),
                aliases=("market.trade_max_attempts",),
            ),
            market_buy_max_hold_seconds=_float(
                controls_flat,
                "market_buy_max_hold_seconds",
                _float(default_controls_flat, "market_buy_max_hold_seconds", 0.0),
                aliases=("market.buy_max_hold_seconds",),
            ),
            market_buy_hold_segments=_market_buy_hold_segments(controls_market, "buy_hold_segments"),
            market_sell_quantity_restore_taps=_integer(
                controls_flat,
                "market_sell_quantity_restore_taps",
                _integer(default_controls_flat, "market_sell_quantity_restore_taps", 0),
                aliases=("market.sell_quantity_restore_taps",),
            ),
            market_sell_quantity_restore_tap_delay_seconds=_float(
                controls_flat,
                "market_sell_quantity_restore_tap_delay_seconds",
                _float(default_controls_flat, "market_sell_quantity_restore_tap_delay_seconds", 0.0),
                aliases=("market.sell_quantity_restore_tap_delay_seconds",),
            ),
            market_critical_level_multiplier=_float(
                controls_flat,
                "market_critical_level_multiplier",
                _float(default_controls_flat, "market_critical_level_multiplier", 0.0),
                aliases=("market.critical_level_multiplier",),
            ),
            haul_post_sell_settle_seconds=_float(
                controls_flat,
                "haul_post_sell_settle_seconds",
                _float(default_controls_flat, "haul_post_sell_settle_seconds", 0.0),
                aliases=("haul.post_sell_settle_seconds",),
            ),
            haul_two_way_auto_hyperspace_engage=_boolean(
                controls_flat,
                "haul_two_way_auto_hyperspace_engage",
                _boolean(default_controls_flat, "haul_two_way_auto_hyperspace_engage", False),
                aliases=("haul.two_way.auto_hyperspace_engage",),
            ),
            haul_two_way_open_nav_panel_after_hyperspace_arrival=_boolean(
                controls_flat,
                "haul_two_way_open_nav_panel_after_hyperspace_arrival",
                _boolean(default_controls_flat, "haul_two_way_open_nav_panel_after_hyperspace_arrival", False),
                aliases=("haul.two_way.open_nav_panel_after_hyperspace_arrival",),
            ),
            haul_two_way_nav_panel_open_delay_seconds=_float(
                controls_flat,
                "haul_two_way_nav_panel_open_delay_seconds",
                _float(default_controls_flat, "haul_two_way_nav_panel_open_delay_seconds", 0.0),
                aliases=("haul.two_way.nav_panel_open_delay_seconds",),
            ),
        ),
        screen=ScreenConfig(
            resolution_width=_integer(screen, "resolution_width", _integer(default_screen, "resolution_width", 0)),
            resolution_height=_integer(screen, "resolution_height", _integer(default_screen, "resolution_height", 0)),
            scale=_float(screen, "scale", _float(default_screen, "scale", 0.0)),
            capture_debug_path=_optional_path(screen.get("capture_debug_path")),
            capture=CaptureConfig(
                mode=_string(screen_capture, "mode", _string(default_screen_capture, "mode", "")),
                base_region=_capture_region(
                    screen_capture,
                    (0.0, 0.0, 1.0, 1.0),
                ),
                regions=capture_regions,
            ),
        ),
        runtime=RuntimeConfig(
            platform=_string(runtime, "platform", default_runtime_platform()),
            debug=_boolean(runtime, "debug", _boolean(default_runtime, "debug", True)),
        ),
        timing=TimingConfig(
            enabled=_boolean(timing, "enabled", _boolean(default_timing, "enabled", True)),
            distribution=_string(
                timing,
                "distribution",
                _string(default_timing, "distribution", "log_normal"),
            ),
            delay=_timing_channel(timing_delay, default_timing_delay),
            hold=_timing_channel(timing_hold, default_timing_hold),
            typing=_timing_channel(timing_typing, default_timing_typing),
        ),
        control_room=ControlRoomConfig(
            state_file=Path(
                _string(control_room, "state_file", _string(default_control_room, "state_file", ""))
            ).expanduser(),
            history_limit=_integer(control_room, "history_limit", _integer(default_control_room, "history_limit", 0)),
            activity_log_max_lines=_integer(
                control_room,
                "activity_log_max_lines",
                _integer(default_control_room, "activity_log_max_lines", 0),
            ),
            command_delay_seconds=_float(
                control_room,
                "command_delay_seconds",
                _float(default_control_room, "command_delay_seconds", 0.0),
            ),
            status_refresh_seconds=_float(
                control_room,
                "status_refresh_seconds",
                _float(default_control_room, "status_refresh_seconds", 0.0),
            ),
            check_for_updates=_boolean(
                control_room,
                "check_for_updates",
                _boolean(default_control_room, "check_for_updates", True),
            ),
            home_system=_string(control_room, "home_system", _string(default_control_room, "home_system", "")),
            clear_session_on_launch=_boolean(
                control_room,
                "clear_session_on_launch",
                _boolean(default_control_room, "clear_session_on_launch", False),
            ),
        ),
        tts=TTSConfig(
            enabled=_boolean(tts, "enabled", _boolean(default_tts, "enabled", True)),
            title_mode=_string(tts, "title_mode", _string(default_tts, "title_mode", "commander")),
            title=_string(tts, "title", _string(default_tts, "title", "commander")),
            disabled_messages=(
                _string_list(tts, "disabled_messages")
                if "disabled_messages" in tts
                else _string_list(default_tts, "disabled_messages")
            ),
            phrases={
                **_string_dict(default_tts, "phrases"),
                **_string_dict(tts, "phrases"),
            },
        ),
        messages=MessagesConfig(
            templates={
                **_string_dict(default_messages, "templates"),
                **_string_dict(messages, "templates"),
            },
        ),
        error_messages=ErrorMessagesConfig(
            templates={
                **_message_template_dict(default_error_messages, "templates"),
                **_message_template_dict(error_messages, "templates"),
            },
        ),
    )
    return validate_config(config)
