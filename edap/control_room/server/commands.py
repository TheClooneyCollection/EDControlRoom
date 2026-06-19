from __future__ import annotations

from typing import Any, Protocol

from edap.control_room_state import CommandHistoryEntry


class ObserverSessionCommandHandler(Protocol):
    def submit_input(self, raw_input: str, *, skip_delay: bool | None = None) -> None: ...

    def open_replay_browser(self) -> None: ...

    def close_replay_browser(self) -> None: ...

    def set_replay_filter(self, filter_text: str) -> None: ...

    def replay_history_entry(
        self,
        entry: CommandHistoryEntry,
        *,
        edit: bool,
        skip_delay: bool = False,
    ) -> None: ...

    def toggle_replay_default_haul(self, entry: CommandHistoryEntry) -> None: ...


def command_history_entry_from_payload(payload: dict[str, object]) -> CommandHistoryEntry | None:
    raw_command = payload.get("raw_command")
    command_name = payload.get("command_name")
    arguments_value = payload.get("arguments", {})
    timestamp = payload.get("timestamp", "")
    if not isinstance(raw_command, str) or not isinstance(command_name, str):
        return None
    if not isinstance(arguments_value, dict):
        return None
    if not isinstance(timestamp, str):
        timestamp = ""
    return CommandHistoryEntry(
        raw=raw_command,
        command=command_name,
        params={str(key): value for key, value in arguments_value.items()},
        timestamp=timestamp,
    )
