from __future__ import annotations

from pathlib import Path
import tomllib


DEFAULT_HAUL_SEARCH_CONFIG_PATH = Path("haul_search.toml")

_STRING_FIELDS = (
    "max_route_distance_ly",
    "max_price_age_hours",
    "max_station_distance_ls",
    "min_supply",
    "min_demand",
    "order_by",
    "min_landing_pad",
    "use_surface_stations",
)

_INT_FIELDS = ("cargo_capacity",)
_BOOL_FIELDS = ("include_round_trips",)


class HaulSearchConfigError(ValueError):
    """Raised when haul-search config parsing fails."""


def _optional_table(raw: dict[str, object], key: str) -> dict[str, object]:
    value = raw.get(key, {})
    if not isinstance(value, dict):
        raise HaulSearchConfigError(f"Haul search config section `{key}` must be a table.")
    return value


def _lookup_string(raw: dict[str, object], key: str) -> str:
    value = raw.get(key)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise HaulSearchConfigError(f"Haul search config value `{key}` must be a string.")
    return value.strip()


def _lookup_int(raw: dict[str, object], key: str) -> str:
    value = raw.get(key)
    if value is None:
        return ""
    if isinstance(value, bool) or not isinstance(value, int):
        raise HaulSearchConfigError(f"Haul search config value `{key}` must be an integer.")
    return str(value)


def _lookup_bool(raw: dict[str, object], key: str) -> str:
    value = raw.get(key)
    if value is None:
        return ""
    if not isinstance(value, bool):
        raise HaulSearchConfigError(f"Haul search config value `{key}` must be true or false.")
    return "true" if value else "false"


def load_haul_search_config(path: Path | str = DEFAULT_HAUL_SEARCH_CONFIG_PATH) -> dict[str, str]:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Haul search config file not found: {config_path}")
    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)

    if not isinstance(raw, dict):
        raise HaulSearchConfigError("Haul search config root must be a TOML table.")

    search = _optional_table(raw, "haul_search")
    root = search or raw

    loaded: dict[str, str] = {}
    for key in _STRING_FIELDS:
        loaded[key] = _lookup_string(root, key)
    for key in _INT_FIELDS:
        loaded[key] = _lookup_int(root, key)
    for key in _BOOL_FIELDS:
        loaded[key] = _lookup_bool(root, key)
    return loaded
