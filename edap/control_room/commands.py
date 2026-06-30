"""Command dispatch and the simple, no-routine commands."""
from __future__ import annotations

from dataclasses import replace

from rich.markup import escape

from edap.config import DEFAULT_CONFIG_PATH, save_home_system
from edap.control_room import error_text
from edap.control_room.help import CONTROL_ROOM_COMMAND_INDEX, CONTROL_ROOM_COMMANDS
from edap.control_room.history import now_iso
from edap.control_room.interfaces import CommandHost
from edap.control_room_state import CommandHistoryEntry
from edap.platform.input.base import DEFAULT_AUTO_TARGET_PROCESS_NAME

def dispatch(app: CommandHost, raw: str, *, skip_delay_override: bool | None = None) -> None:
    if not raw.strip():
        return
    app._log(f"[dim]Command: {escape(raw)}[/]")
    skip_delay = False
    command_raw = raw
    if command_raw.startswith("!"):
        skip_delay = True
        command_raw = command_raw[1:].lstrip()
        if not command_raw:
            app._log("[dim]Unknown command: ![/]")
            return
    if skip_delay_override is not None:
        skip_delay = skip_delay_override

    cmd = command_raw.lower()
    if cmd in {"q", "quit", "exit"}:
        app._record_history_entry(CommandHistoryEntry(raw=raw, command="quit", timestamp=now_iso()))
        app._request_shutdown("quit command")
        return

    parts = cmd.split(None, 1)
    verb = parts[0]
    rest = parts[1].strip() if len(parts) > 1 else ""
    raw_parts = command_raw.split(None, 1)
    raw_rest = raw_parts[1].strip() if len(raw_parts) > 1 else ""

    if verb == "dock":
        app._record_history_entry(CommandHistoryEntry(raw=raw, command="dock", timestamp=now_iso()))
        app._cmd_dock(skip_delay=skip_delay)
    elif verb == "undock":
        app._record_history_entry(CommandHistoryEntry(raw=raw, command="undock", timestamp=now_iso()))
        app._cmd_undock(skip_delay=skip_delay)
    elif verb == "jump":
        app._record_history_entry(CommandHistoryEntry(raw=raw, command="jump", timestamp=now_iso()))
        app._cmd_jump(skip_delay=skip_delay)
    elif verb == "escape":
        app._record_history_entry(CommandHistoryEntry(raw=raw, command="escape", timestamp=now_iso()))
        app._cmd_escape(skip_delay=skip_delay)
    elif verb == "boost":
        app._record_history_entry(CommandHistoryEntry(raw=raw, command="boost", timestamp=now_iso()))
        app._cmd_boost(skip_delay=skip_delay)
    elif verb == "buy":
        app._cmd_buy(raw_rest, skip_delay=skip_delay)
    elif verb == "sell":
        app._cmd_sell(raw_rest, skip_delay=skip_delay)
    elif verb == "haul":
        app._cmd_haul(raw_rest, skip_delay=skip_delay, raw_command=raw)
    elif verb in {"multi_leg_haul", "mult"}:
        app._cmd_multi_leg_haul(raw_rest, skip_delay=skip_delay, raw_command=raw)
    elif verb in {"dest", "set_dest"}:
        if not raw_rest:
            app._log(f"[red]{escape(error_text.render(app._config, 'dest_usage'))}[/]")
        else:
            app._cmd_dest(raw_rest, skip_delay=skip_delay, raw_command=raw)
    elif verb == "home":
        if not raw_rest:
            cmd_home(app, raw=raw, skip_delay=skip_delay)
        elif raw_rest.lower() == "set" or raw_rest.lower().startswith("set "):
            system_name = raw_rest[3:].strip()
            cmd_home_set(app, system_name, raw=raw)
        else:
            app._record_history_entry(
                CommandHistoryEntry(
                    raw=raw,
                    command="home",
                    params={"value": raw_rest},
                    timestamp=now_iso(),
                )
            )
            app._log(f"[red]{escape(error_text.render(app._config, 'home_usage'))}[/]")
    elif verb == "market":
        app._record_history_entry(CommandHistoryEntry(raw=raw, command="market", params={"value": raw_rest}, timestamp=now_iso()))
        cmd_market(app, raw_rest)
    elif verb == "verbose":
        app._record_history_entry(CommandHistoryEntry(raw=raw, command="verbose", params={"value": rest}, timestamp=now_iso()))
        cmd_verbose(app, rest)
    elif verb == "instant":
        app._record_history_entry(CommandHistoryEntry(raw=raw, command="instant", params={"value": rest}, timestamp=now_iso()))
        cmd_instant(app, rest)
    elif verb in {"new_session", "clear"}:
        app._record_history_entry(
            CommandHistoryEntry(raw=raw, command="new_session", timestamp=now_iso())
        )
        cmd_new_session(app)
    elif verb == "stop":
        app._record_history_entry(
            CommandHistoryEntry(raw=raw, command="stop", timestamp=now_iso())
        )
        cmd_stop_session(app)
    elif verb == "set_pid":
        app._record_history_entry(
            CommandHistoryEntry(raw=raw, command="set_pid", params={"value": raw_rest}, timestamp=now_iso())
        )
        cmd_set_pid(app, raw_rest)
    elif verb == "set_hwnd":
        app._record_history_entry(
            CommandHistoryEntry(raw=raw, command="set_hwnd", params={"value": raw_rest}, timestamp=now_iso())
        )
        cmd_set_hwnd(app, raw_rest)
    elif verb == "commands":
        app._record_history_entry(CommandHistoryEntry(raw=raw, command="commands", timestamp=now_iso()))
        cmd_commands(app)
    elif verb in {"help", "?"}:
        app._record_history_entry(CommandHistoryEntry(raw=raw, command="help", params={"topic": raw_rest}, timestamp=now_iso()))
        cmd_help(app, raw_rest)
    elif verb in {"replay", "history"}:
        app._record_history_entry(CommandHistoryEntry(raw=raw, command="replay", timestamp=now_iso()))
        cmd_resume(app)
    elif verb == "reload":
        app._cmd_reload()
    else:
        app._record_history_entry(
            CommandHistoryEntry(
                raw=raw,
                command=verb,
                params={"value": raw_rest} if raw_rest else {},
                timestamp=now_iso(),
            )
        )
        app._log(f"[dim]Unknown command: {escape(raw)}[/]")


def cmd_home(app: CommandHost, *, raw: str, skip_delay: bool) -> None:
    home_system = app._config.control_room.home_system.strip()
    if not home_system:
        app._record_history_entry(CommandHistoryEntry(raw=raw, command="home", timestamp=now_iso()))
        app._log(f"[red]{escape(error_text.render(app._config, 'home_not_set'))}[/]")
        return
    app._cmd_dest(home_system, skip_delay=skip_delay, raw_command=raw)


def cmd_home_set(app: CommandHost, system_name: str, *, raw: str) -> None:
    if not system_name:
        system_name = (app._ship.system or "").strip()
        if not system_name:
            app._record_history_entry(CommandHistoryEntry(raw=raw, command="home", timestamp=now_iso()))
            app._log(f"[red]{escape(error_text.render(app._config, 'home_set_system_unknown'))}[/]")
            return

    target_path = (
        app._config_path.with_name(DEFAULT_CONFIG_PATH.name)
        if app._config_loaded_from_example_fallback
        else app._config_path
    )
    saved_path = save_home_system(target_path, system_name)
    app._config = replace(
        app._config,
        control_room=replace(app._config.control_room, home_system=system_name),
    )
    app._record_history_entry(
        CommandHistoryEntry(
            raw=raw,
            command="home",
            params={"mode": "set", "system": system_name},
            timestamp=now_iso(),
        )
    )
    app._log(
        f"[green]Home system saved:[/] [bold]{escape(system_name)}[/] "
        f"[dim]({escape(str(saved_path))})[/]"
    )


def cmd_commands(app: CommandHost) -> None:
    app._log("[dim]Supported commands:[/]")
    for command in CONTROL_ROOM_COMMANDS:
        aliases = f" [dim](aliases: {', '.join(command.aliases)})[/]" if command.aliases else ""
        app._log(f"[bold]{escape(command.usage)}[/] — {escape(command.summary)}{aliases}")


def cmd_resume(app: CommandHost) -> None:
    app._show_resume_picker()


def cmd_help(app: CommandHost, rest: str) -> None:
    topic = rest.strip().lower()
    if not topic:
        app._log("[dim]Use [bold]commands[/] to list everything, or [bold]help <command>[/] for one command in plain English.[/]")
        return

    command = CONTROL_ROOM_COMMAND_INDEX.get(topic)
    if command is None:
        app._log(
            f"[red]{escape(error_text.render(app._config, 'unknown_help_topic', topic=rest))}[/]"
        )
        return

    aliases = f"  Aliases: {', '.join(command.aliases)}" if command.aliases else ""
    app._log(
        f"[bold]{escape(command.name)}[/] — {escape(command.usage)}"
        f"{f'[dim]{escape(aliases)}[/]' if aliases else ''}"
    )
    app._log(escape(command.detail))


def cmd_verbose(app: CommandHost, rest: str) -> None:
    if rest in {"on", "1", "true"}:
        app._verbose_controls = True
        app._log("[dim]Verbose key logging on — key presses will appear in the activity log.[/]")
    elif rest in {"off", "0", "false", ""}:
        app._verbose_controls = False
        app._log("[dim]Verbose key logging off.[/]")
    else:
        state = "on" if app._verbose_controls else "off"
        app._log(f"[dim]verbose {state}  —  use: verbose on | verbose off[/]")


def cmd_instant(app: CommandHost, rest: str) -> None:
    value = rest.strip().lower()
    if value in {"", "toggle"}:
        app._instant_mode = not app._instant_mode
    elif value in {"on", "1", "true"}:
        app._instant_mode = True
    elif value in {"off", "0", "false"}:
        app._instant_mode = False
    else:
        state = "on" if app._instant_mode else "off"
        app._log(f"[dim]instant {state}  —  use: instant | instant on | instant off[/]")
        return

    if app._instant_mode:
        app._log("[dim]Instant mode on — command launch delay is disabled until you turn it off.[/]")
    else:
        delay_s = app._config.control_room.command_delay_seconds
        app._log(f"[dim]Instant mode off — command launch delay restored to {delay_s:.1f}s.[/]")
    app._saved_state.instant_mode = app._instant_mode
    app._save_saved_state()


def cmd_set_pid(app: CommandHost, rest: str) -> None:
    value = rest.strip()
    try:
        if _is_foreground_target_value(value):
            summary = app._set_foreground_input_target()
        elif value:
            parsed_pid = _parse_int_target(value)
            if parsed_pid is not None:
                summary = app._set_pid_input_target(parsed_pid)
            else:
                summary = app._auto_target_input(value, prefer="pid")
        else:
            summary = app._auto_target_input(DEFAULT_AUTO_TARGET_PROCESS_NAME, prefer="pid")
    except (RuntimeError, ValueError) as exc:
        app._log(f"[red]{escape(str(exc))}[/]")
        return
    app._log(f"[dim]Input target: {escape(summary)}[/]")


def cmd_set_hwnd(app: CommandHost, rest: str) -> None:
    value = rest.strip()
    try:
        if _is_foreground_target_value(value):
            summary = app._set_foreground_input_target()
        elif value:
            parsed_hwnd = _parse_int_target(value)
            if parsed_hwnd is not None:
                summary = app._set_hwnd_input_target(parsed_hwnd)
            else:
                summary = app._auto_target_input(value, prefer="hwnd")
        else:
            summary = app._auto_target_input(DEFAULT_AUTO_TARGET_PROCESS_NAME, prefer="hwnd")
    except (RuntimeError, ValueError) as exc:
        app._log(f"[red]{escape(str(exc))}[/]")
        return
    app._log(f"[dim]Input target: {escape(summary)}[/]")


def cmd_market(app: CommandHost, rest: str) -> None:
    rest_lower = rest.lower()
    if rest_lower == "lock":
        app._lock_market_display()
    elif rest_lower == "unlock":
        app._unlock_market_display()
    elif rest_lower.startswith("filter "):
        term = rest[7:].strip()
        if not term:
            app._log(f"[red]{escape(error_text.render(app._config, 'market_filter_usage'))}[/]")
            return
        app._set_market_filter(term)
    else:
        app._clear_market_filter()


def cmd_new_session(app: CommandHost) -> None:
    app._clear_session_stats()
    app._log("[dim]Started a new persisted haul session.[/]")


def cmd_stop_session(app: CommandHost) -> None:
    try:
        app._stop_session_stats()
    except ValueError as exc:
        app._log(f"[yellow]{escape(str(exc))}[/]")
        return
    app._log("[dim]Stopped the persisted haul session.[/]")


def _is_foreground_target_value(value: str) -> bool:
    return value.lower() in {"foreground", "clear", "off", "none"}


def _parse_int_target(value: str) -> int | None:
    try:
        parsed = int(value, 0)
    except ValueError:
        return None
    if parsed <= 0:
        raise ValueError("Target identifiers must be positive integers.")
    return parsed
