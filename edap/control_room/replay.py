from __future__ import annotations

from typing import Protocol

from rich.markup import escape
from rich.text import Text
from textual.containers import Vertical
from textual.widgets import Input, OptionList, RichLog, Static

from edap.config import AppConfig
from edap.control_room import history as _history
from edap.control_room import prompts as _prompts
from edap.control_room.models import ReplaySelection
from edap.control_room_state import CommandHistoryEntry, ControlRoomState


class ReplayHost(Protocol):
    _config: AppConfig
    _prompt_state: object
    _saved_state: ControlRoomState
    _resume_entries: list[ReplaySelection]
    _resume_open: bool
    _resume_filter: str
    _selected_resume_history_entry: CommandHistoryEntry | None
    _haul_params: dict[str, str]

    def _log(self, msg: str) -> None: ...
    def _save_saved_state(self) -> None: ...
    def _dispatch_command(self, raw: str, *, skip_delay: bool | None = None) -> None: ...
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
    def _start_haul_prompt(
        self,
        *,
        commodity: str,
        prompt_for_commodity: bool,
        seed: dict[str, str] | None = None,
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None: ...
    def _start_haul_search_prompt(
        self,
        *,
        system_name: str,
        seed: dict[str, str] | None = None,
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None: ...
    def _start_dest_prompt(
        self,
        destination: str,
        *,
        settle_default: float | None = None,
        skip_delay: bool = False,
        raw_command: str | None = None,
    ) -> None: ...
    def set_focus(self, widget: object) -> None: ...
    def query_one(self, selector: str, widget_type: object | None = None) -> object: ...


def default_haul_matches(app: ReplayHost, entry: CommandHistoryEntry) -> bool:
    return _history.default_haul_matches(entry, app._saved_state.default_haul)


def filtered_resume_entries(app: ReplayHost) -> list[ReplaySelection]:
    return _history.filtered_resume_entries(
        app._saved_state.history,
        app._saved_state.default_haul,
        app._resume_filter,
    )


def refresh_resume_help(app: ReplayHost) -> None:
    filter_label = app._resume_filter or "none"
    help_text = (
        "Replay history  |  Enter execute  |  ! execute now  |  e edit  |  * set default haul  |  "
        "type prefix filter  |  Backspace delete  |  Esc/q close\n"
        f"Filter: {filter_label}"
    )
    app.query_one("#resume-help", Static).update(help_text)


def show_resume_picker(app: ReplayHost) -> None:
    if not app._saved_state.history:
        app._log("[dim]No saved command history yet.[/]")
        return

    app._resume_filter = ""
    app._resume_entries = filtered_resume_entries(app)
    option_list = app.query_one("#resume-list", OptionList)
    option_list.clear_options()
    option_list.add_options([item.label for item in app._resume_entries])
    app._selected_resume_history_entry = app._resume_entries[0].entry if app._resume_entries else None
    sync_resume_widget_selection(app)
    app._resume_open = True
    app.query_one("#activity", RichLog).styles.display = "none"
    app.query_one("#resume-browser", Vertical).styles.display = "block"
    refresh_resume_help(app)
    update_resume_detail(app)
    app.set_focus(option_list)


def refresh_resume_picker(app: ReplayHost) -> None:
    if not app._resume_open:
        return
    option_list = app.query_one("#resume-list", OptionList)
    selected_entry = selected_resume_entry(app)
    app._resume_entries = filtered_resume_entries(app)
    option_list.clear_options()
    option_list.add_options([item.label for item in app._resume_entries])
    app._selected_resume_history_entry = _resolve_selected_entry(app, selected_entry)
    sync_resume_widget_selection(app)
    refresh_resume_help(app)
    update_resume_detail(app)


def close_resume_picker(app: ReplayHost) -> None:
    app._resume_open = False
    app._resume_filter = ""
    app._selected_resume_history_entry = None
    app.query_one("#resume-browser", Vertical).styles.display = "none"
    app.query_one("#activity", RichLog).styles.display = "block"
    app.set_focus(app.query_one("#cmd", Input))


def selected_resume_entry(app: ReplayHost) -> CommandHistoryEntry | None:
    return _resolve_selected_entry(app, app._selected_resume_history_entry)


def sync_selected_resume_entry_from_widget(app: ReplayHost) -> None:
    if not app._resume_entries:
        app._selected_resume_history_entry = None
        return
    option_list = app.query_one("#resume-list", OptionList)
    index = option_list.highlighted
    if index is None or index < 0 or index >= len(app._resume_entries):
        app._selected_resume_history_entry = app._resume_entries[0].entry
        return
    app._selected_resume_history_entry = app._resume_entries[index].entry


def sync_resume_widget_selection(app: ReplayHost) -> None:
    option_list = app.query_one("#resume-list", OptionList)
    if not app._resume_entries:
        option_list.highlighted = None
        return
    selected_entry = _resolve_selected_entry(app, app._selected_resume_history_entry)
    app._selected_resume_history_entry = selected_entry
    selected_index = 0
    for index, replay_entry in enumerate(app._resume_entries):
        if replay_entry.entry == selected_entry:
            selected_index = index
            break
    option_list.highlighted = selected_index


def move_resume_selection(app: ReplayHost, offset: int) -> None:
    if not app._resume_entries or offset == 0:
        return
    selected_entry = _resolve_selected_entry(app, app._selected_resume_history_entry)
    current_index = 0
    for index, replay_entry in enumerate(app._resume_entries):
        if replay_entry.entry == selected_entry:
            current_index = index
            break
    next_index = max(0, min(len(app._resume_entries) - 1, current_index + offset))
    app._selected_resume_history_entry = app._resume_entries[next_index].entry
    sync_resume_widget_selection(app)
    update_resume_detail(app)


def update_resume_detail(app: ReplayHost) -> None:
    detail = "[dim]No selection[/]"
    entry = selected_resume_entry(app)
    if entry is not None:
        detail = escape(_history.resume_detail(entry))
    app.query_one("#resume-detail", Static).update(Text.from_markup(detail))


def resume_execute_selected(app: ReplayHost) -> None:
    entry = selected_resume_entry(app)
    if entry is None:
        return
    close_resume_picker(app)
    replay_history_entry(app, entry, edit=False)


def resume_execute_selected_immediate(app: ReplayHost) -> None:
    entry = selected_resume_entry(app)
    if entry is None:
        return
    close_resume_picker(app)
    replay_history_entry(app, entry, edit=False, skip_delay=True)


def resume_edit_selected(app: ReplayHost) -> None:
    entry = selected_resume_entry(app)
    if entry is None:
        return
    close_resume_picker(app)
    replay_history_entry(app, entry, edit=True)


def resume_toggle_default_selected(app: ReplayHost) -> None:
    entry = selected_resume_entry(app)
    if entry is None:
        return
    if entry.command != "haul" or _history.is_haul_search_entry(entry):
        app._log("[dim]Only two-station haul loop entries can be saved as the default.[/]")
        return
    if default_haul_matches(app, entry):
        app._saved_state.default_haul = {}
        app._log("[dim]Cleared saved default haul.[/]")
    else:
        app._saved_state.default_haul = {
            str(key): str(value) for key, value in entry.params.items()
        }
        cargo = app._saved_state.default_haul.get("station_1_buying", "haul")
        app._log(f"[dim]Saved default haul from history: {escape(cargo)}[/]")
    app._save_saved_state()
    refresh_resume_picker(app)


def replay_history_entry(
    app: ReplayHost,
    entry: CommandHistoryEntry,
    *,
    edit: bool,
    skip_delay: bool = False,
) -> None:
    if edit:
        if entry.command == "haul":
            if _history.is_haul_search_entry(entry):
                seed = {
                    str(key): str(value)
                    for key, value in entry.params.items()
                    if str(key) != "mode"
                }
                system_name = seed.get("near_system", "").strip()
                if system_name:
                    app._start_haul_search_prompt(
                        system_name=system_name,
                        seed=seed,
                        skip_delay=skip_delay,
                        raw_command=entry.raw,
                    )
                    return
            app._start_haul_prompt(
                commodity="",
                prompt_for_commodity=True,
                seed={str(key): str(value) for key, value in entry.params.items()},
                skip_delay=skip_delay,
                raw_command=entry.raw,
            )
            return
        if entry.command == "dest":
            destination = str(entry.params.get("destination", "")).strip()
            if destination:
                settle_value = entry.params.get("galaxy_map_settle")
                settle_default = float(settle_value) if settle_value is not None else None
                app._start_dest_prompt(
                    destination,
                    settle_default=settle_default,
                    skip_delay=skip_delay,
                    raw_command=entry.raw,
                )
                return
        cmd_input = app.query_one("#cmd", Input)
        cmd_input.value = entry.raw
        cmd_input.cursor_position = len(cmd_input.value)
        _prompts.set_command_input_prefill(
            app._prompt_state,
            placeholder=getattr(cmd_input, "placeholder", ""),
            value=entry.raw,
        )
        app.set_focus(cmd_input)
        return

    if entry.command == "haul":
        if _history.is_haul_search_entry(entry):
            params = {
                str(key): str(value)
                for key, value in entry.params.items()
                if str(key) != "mode"
            }
            system_name = params.pop("near_system", "").strip()
            if system_name:
                app._dispatch_haul_search(
                    system_name=system_name,
                    query_params=params,
                    skip_delay=skip_delay or entry.raw.startswith("!"),
                    raw_command=entry.raw,
                )
            return
        app._haul_params = {str(key): str(value) for key, value in entry.params.items()}
        app._dispatch_haul_loop(
            skip_delay=skip_delay or entry.raw.startswith("!"),
            raw_command=entry.raw,
        )
        return
    if entry.command == "dest":
        destination = str(entry.params.get("destination", "")).strip()
        if destination:
            settle_value = entry.params.get("galaxy_map_settle")
            settle = (
                float(settle_value)
                if settle_value is not None
                else app._config.controls.galaxy_map_settle_seconds
            )
            app._dispatch_dest(
                destination,
                settle,
                skip_delay=skip_delay or entry.raw.startswith("!"),
                raw_command=entry.raw,
            )
        return

    app._dispatch_command(
        entry.raw,
        skip_delay=(True if skip_delay else None),
    )


def _resolve_selected_entry(
    app: ReplayHost,
    selected_entry: CommandHistoryEntry | None,
) -> CommandHistoryEntry | None:
    if not app._resume_entries:
        return None
    if selected_entry is None:
        return app._resume_entries[0].entry
    for replay_entry in app._resume_entries:
        if replay_entry.entry == selected_entry:
            return replay_entry.entry
    return app._resume_entries[0].entry
