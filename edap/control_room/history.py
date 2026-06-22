from __future__ import annotations

from datetime import UTC, datetime
from typing import Mapping, Sequence

from edap.control_room.models import ReplaySelection
from edap.control_room_state import CommandHistoryEntry


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def resume_summary(entry: CommandHistoryEntry) -> str:
    prefix = entry.timestamp or "?"
    return f"{prefix}  {entry.raw}"


def resume_detail(entry: CommandHistoryEntry) -> str:
    if not entry.params:
        return entry.raw
    parts = [f"{key}={value}" for key, value in entry.params.items()]
    return f"{entry.raw}\n" + "\n".join(parts)


def is_haul_search_entry(entry: CommandHistoryEntry) -> bool:
    return entry.command == "haul" and str(entry.params.get("mode", "")).strip().lower() == "search"


def default_haul_matches(entry: CommandHistoryEntry, default_haul: Mapping[str, str]) -> bool:
    return (
        entry.command == "haul"
        and not is_haul_search_entry(entry)
        and bool(default_haul)
        and default_haul.get("mode", "").strip().lower() != "search"
        and entry.params == default_haul
    )


def resume_label(entry: CommandHistoryEntry, default_haul: Mapping[str, str]) -> str:
    marker = "* " if default_haul_matches(entry, default_haul) else "  "
    return marker + resume_summary(entry)


def filtered_resume_entries(
    history: Sequence[CommandHistoryEntry],
    default_haul: Mapping[str, str],
    prefix: str,
) -> list[ReplaySelection]:
    needle = prefix.lower()
    matched = [
        entry for entry in reversed(history)
        if not needle or entry.raw.lower().startswith(needle)
    ]
    if default_haul:
        pinned = [e for e in matched if default_haul_matches(e, default_haul)]
        rest = [e for e in matched if not default_haul_matches(e, default_haul)]
        matched = pinned[:1] + rest
    return [
        ReplaySelection(
            entry=entry,
            label=resume_label(entry, default_haul),
            detail=resume_detail(entry),
        )
        for entry in matched
    ]
