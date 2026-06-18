from __future__ import annotations

from pathlib import Path
import tomllib


DEFAULT_HAUL_CONFIG_PATH = Path("haul.toml")


class HaulConfigError(ValueError):
    """Raised when haul config parsing fails."""


def _optional_table(raw: dict[str, object], key: str) -> dict[str, object]:
    value = raw.get(key, {})
    if not isinstance(value, dict):
        raise HaulConfigError(f"Haul config section `{key}` must be a table.")
    return value


def _lookup_string(raw: dict[str, object], key: str, *, default: str = "") -> str:
    value = raw.get(key, default)
    if value is None:
        return default
    if isinstance(value, dict):
        return default
    if not isinstance(value, str):
        raise HaulConfigError(f"Haul config value `{key}` must be a string.")
    return value.strip()


def _lookup_float(raw: dict[str, object], key: str) -> str:
    value = raw.get(key)
    if value is None:
        return ""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise HaulConfigError(f"Haul config value `{key}` must be a number.")
    return str(float(value))


def _lookup_bool(raw: dict[str, object], key: str) -> str:
    value = raw.get(key)
    if value is None:
        return ""
    if not isinstance(value, bool):
        raise HaulConfigError(f"Haul config value `{key}` must be true or false.")
    return "true" if value else "false"


def load_haul_config(path: Path | str = DEFAULT_HAUL_CONFIG_PATH) -> dict[str, str]:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Haul config file not found: {config_path}")
    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)

    if not isinstance(raw, dict):
        raise HaulConfigError("Haul config root must be a TOML table.")

    haul = _optional_table(raw, "haul")
    root = haul or raw
    station_1 = _optional_table(root, "station_1")
    station_2 = _optional_table(root, "station_2")

    return {
        "station_1_buying": _lookup_string(root, "station_1_buying")
        or _lookup_string(station_1, "buying"),
        "station_1": _lookup_string(root, "station_1") or _lookup_string(station_1, "name"),
        "station_1_system": _lookup_string(root, "station_1_system")
        or _lookup_string(station_1, "system"),
        "station_1_on_land": _lookup_bool(root, "station_1_on_land")
        or _lookup_bool(station_1, "on_land"),
        "station_2_buying": _lookup_string(root, "station_2_buying")
        or _lookup_string(station_2, "buying"),
        "station_2": _lookup_string(root, "station_2") or _lookup_string(station_2, "name"),
        "station_2_system": _lookup_string(root, "station_2_system")
        or _lookup_string(station_2, "system"),
        "station_2_on_land": _lookup_bool(root, "station_2_on_land")
        or _lookup_bool(station_2, "on_land"),
        "galaxy_map_settle": _lookup_float(root, "galaxy_map_settle")
        or _lookup_float(root, "galaxy_map_settle_seconds"),
        "dock_timeout": _lookup_float(root, "dock_timeout")
        or _lookup_float(root, "dock_timeout_seconds"),
    }
