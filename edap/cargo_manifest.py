from __future__ import annotations

import json
from pathlib import Path
from time import sleep
from typing import Any, Callable

from edap.status import read_status


def commodity_name_key(value: object) -> str:
    raw = str(value or "").strip().lower()
    if raw.startswith("$"):
        raw = raw[1:]
    if raw.endswith(";"):
        raw = raw[:-1]
    if raw.endswith("_name"):
        raw = raw[:-5]
    return "".join(ch for ch in raw if ch.isalnum())


def cargo_item_matches_commodity(item: dict[str, Any], commodity: str) -> bool:
    target_key = commodity_name_key(commodity)
    if not target_key:
        return False
    return any(
        commodity_name_key(item.get(key)) == target_key
        for key in ("Name", "Name_Localised")
    )


def _read_cargo_inventory_once(journal_dir: Path) -> list[dict[str, Any]]:
    cargo_path = journal_dir / "Cargo.json"
    try:
        with cargo_path.open(encoding="utf-8") as handle:
            cargo_data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return []
    inventory = cargo_data.get("Inventory", [])
    return inventory if isinstance(inventory, list) else []


def _status_cargo_count(journal_dir: Path) -> int | None:
    try:
        status = read_status(journal_dir)
    except Exception:
        status = None
    if status is None or status.cargo is None:
        return None
    return int(status.cargo)


def read_cargo_inventory(
    journal_dir: Path,
    *,
    retry_attempts_when_status_has_cargo: int = 3,
    retry_delay_s: float = 0.1,
    sleeper: Callable[[float], None] = sleep,
) -> list[dict[str, Any]]:
    expected_cargo_count = _status_cargo_count(journal_dir) or 0
    attempts = retry_attempts_when_status_has_cargo if expected_cargo_count > 0 else 1
    attempts = max(1, attempts)

    inventory: list[dict[str, Any]] = []
    for attempt in range(attempts):
        inventory = _read_cargo_inventory_once(journal_dir)
        if inventory or expected_cargo_count <= 0:
            return inventory
        if attempt < attempts - 1 and retry_delay_s > 0:
            sleeper(retry_delay_s)
    return inventory
