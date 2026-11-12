"""`say` and `voice`: speak free text and tune the host Piper voice."""
from __future__ import annotations

from dataclasses import replace

from rich.markup import escape

from edcr.config import DEFAULT_CONFIG_PATH, PIPER_TUNING_KEYS, PiperVoiceConfig, save_piper_voice
from edcr.control_room.interfaces import CommandHost
from edcr.tts import piper_voice_models

VOICE_USAGE = "Usage: voice | voice set [model=<name>] [<setting>=<number>|default ...] | voice save"


def cmd_say(app: CommandHost, text: str) -> None:
    line = text.strip()
    if not line:
        app._log("[red]Usage: say <text>[/]")
        return
    # Published like a callout, so pages and the hub voice (plan 0015) play it too; a node the hub
    # has muted leaves the speaking to the hub.
    app._publish_announcement("say", line, {})
    if app._tts.muted:
        return
    if not app._tts.say(line):
        app._log("[yellow]TTS is off, nothing spoken.[/] [dim]Set tts.enabled = true and restart.[/]")


def cmd_voice(app: CommandHost, rest: str) -> None:
    action, _, args = rest.strip().partition(" ")
    voice = app._tts.piper_voice
    if voice is None:
        app._log("[yellow]No Piper voice is running.[/] [dim]Configure [tts.piper] and restart to tune the voice.[/]")
        return
    if not action:
        _log_voice(app, voice)
    elif action == "set":
        updated = _voice_with_changes(app, voice, args.split())
        if updated is None:
            return
        app._tts.configure_piper(updated)
        _log_voice(app, updated)
        app._publish_protocol_data_refresh()
    elif action == "save":
        target_path = (
            app._config_path.with_name(DEFAULT_CONFIG_PATH.name)
            if app._config_loaded_from_example_fallback
            else app._config_path
        )
        saved_path = save_piper_voice(target_path, voice)
        app._config = replace(app._config, tts=replace(app._config.tts, piper=voice))
        app._log(f"[green]Voice saved:[/] [bold]{escape(voice.model.stem)}[/] [dim]({escape(str(saved_path))})[/]")
    else:
        app._log(f"[red]{escape(VOICE_USAGE)}[/]")


def _voice_with_changes(app: CommandHost, voice: PiperVoiceConfig, pairs: list[str]) -> PiperVoiceConfig | None:
    changes: dict[str, object] = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep:
            app._log(f"[red]{escape(VOICE_USAGE)}[/]")
            return None
        if key == "model":
            model = next((path for path in piper_voice_models(voice.model) if path.stem == value), None)
            if model is None:
                app._log(f"[red]Unknown voice: {escape(value)}[/]")
                return None
            changes["model"] = model
        elif key in PIPER_TUNING_KEYS:
            number = _tuning_number(value, key=key)
            if number is False:
                app._log(f"[red]Bad value for {escape(key)}: {escape(value)}[/]")
                return None
            changes[key] = number
        else:
            app._log(f"[red]Unknown voice setting: {escape(key)}[/] [dim]({', '.join(PIPER_TUNING_KEYS)})[/]")
            return None
    return replace(voice, **changes)


def _tuning_number(value: str, *, key: str) -> float | None | bool:
    """The parsed number, None for `default`, or False when the value is unusable."""
    if value == "default":
        return None
    try:
        number = float(value)
    except ValueError:
        return False
    if number < 0 or (key == "length_scale" and number == 0) or number != number:
        return False
    return number


def _log_voice(app: CommandHost, voice: PiperVoiceConfig) -> None:
    tuning = ", ".join(
        f"{key}={'default' if (value := getattr(voice, key)) is None else value}"
        for key in PIPER_TUNING_KEYS
    )
    voices = ", ".join(path.stem for path in piper_voice_models(voice.model))
    app._log(f"[green]Voice:[/] [bold]{escape(voice.model.stem)}[/] [dim]{escape(tuning)}. Installed: {escape(voices)}[/]")
