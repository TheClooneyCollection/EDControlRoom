from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping
import tomllib


DEFAULT_HAUL_SEARCH_CONFIG_PATH = Path("haul_search.toml")
DEFAULT_HAUL_SEARCH_DEFAULTS_PATH = Path(__file__).resolve().parent.parent / "defaults" / "haul_search.toml"
GENERATED_HAUL_SEARCH_FIELDS = ("cargo_capacity",)

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
_FIELD_ORDER = (*_INT_FIELDS, *_STRING_FIELDS, *_BOOL_FIELDS)
_FIELD_SET = set(_FIELD_ORDER)


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


def save_haul_search_config(
    params: Mapping[str, object],
    path: Path | str = DEFAULT_HAUL_SEARCH_CONFIG_PATH,
    *,
    exclude: Iterable[str] = (),
) -> Path:
    config_path = Path(path)
    excluded = {str(key) for key in exclude}
    values = {
        key: _format_toml_value(key, str(params[key]).strip())
        for key in _FIELD_ORDER
        if key in params and key not in excluded and str(params[key]).strip()
    }
    if not values:
        return config_path

    existing = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    updated = _upsert_toml_values(existing, section="haul_search", values=values)
    config_path.write_text(updated, encoding="utf-8")
    return config_path


def _format_toml_value(key: str, value: str) -> str:
    if key not in _FIELD_SET:
        raise HaulSearchConfigError(f"Unknown haul search config value `{key}`.")
    if key in _INT_FIELDS:
        try:
            parsed = int(value)
        except ValueError as exc:
            raise HaulSearchConfigError(f"Haul search config value `{key}` must be an integer.") from exc
        if parsed < 0:
            raise HaulSearchConfigError(f"Haul search config value `{key}` must be non-negative.")
        return str(parsed)
    if key in _BOOL_FIELDS:
        lowered = value.lower()
        if lowered not in {"true", "false"}:
            raise HaulSearchConfigError(f"Haul search config value `{key}` must be true or false.")
        return lowered
    return _toml_basic_string(value)


def _toml_basic_string(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\b", "\\b")
        .replace("\t", "\\t")
        .replace("\n", "\\n")
        .replace("\f", "\\f")
        .replace("\r", "\\r")
    )
    return f'"{escaped}"'


def _upsert_toml_values(content: str, *, section: str, values: Mapping[str, str]) -> str:
    lines = content.splitlines(keepends=True)
    section_header = f"[{section}]"
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

    value_lines = {key: f"{key} = {value}\n" for key, value in values.items()}
    if section_start is None:
        prefix = (
            ""
            if not lines or (lines[-1].endswith("\n") and lines[-1].strip() == "")
            else "\n"
        )
        return (
            "".join(lines)
            + prefix
            + section_header
            + "\n"
            + "".join(value_lines.values())
        )

    remaining = dict(value_lines)
    updated: list[str] = []
    for index, line in enumerate(lines):
        if section_start < index < section_end:
            key = line.split("=", 1)[0].strip() if "=" in line else ""
            if key in remaining:
                updated.append(remaining.pop(key))
                continue
        if index == section_end:
            updated.extend(remaining.values())
        updated.append(line)

    if section_end == len(lines):
        updated.extend(remaining.values())
    return "".join(updated)
