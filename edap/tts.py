from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import json
from enum import Enum
import logging
import os
from pathlib import Path
import re
from shutil import which
import subprocess
import tempfile
from threading import Condition, Lock, Thread
from typing import Callable, Mapping, Protocol

from edap.config import PIPER_TUNING_KEYS, PiperVoiceConfig, TTSConfig

logger = logging.getLogger(__name__)


class AnnouncementId(str, Enum):
    STARTUP_GREETING = "startup_greeting"
    DESTINATION_SET = "destination_set"
    FSD_TARGET_LOCKED = "fsd_target_locked"
    FSD_ENGAGE_TRYING = "fsd_engage_trying"
    STATION_CLEARED = "station_cleared"
    SUPERCRUISE_FALLBACK = "supercruise_fallback"
    SUPERCRUISE_COUNTDOWN = "supercruise_countdown"
    FSD_JUMP_BLOCKED = "fsd_jump_blocked"
    UNDER_ATTACK = "under_attack"
    SUPERCRUISE_ESCAPE_ALIGN = "supercruise_escape_align"
    HAUL_ABORTED = "haul_aborted"
    HAUL_CANCELLED = "haul_cancelled"
    HAUL_PAUSE_REQUESTED = "haul_pause_requested"
    HAUL_PAUSED = "haul_paused"
    MANUAL_LANDING = "manual_landing"
    HAUL_STOP_AFTER_RUN = "haul_stop_after_run"
    HAUL_WRONG_CARGO_ABORTED = "haul_wrong_cargo_aborted"
    HAUL_CARGO_STATE_STALE = "haul_cargo_state_stale"
    HAUL_TOP_UP_UNAFFORDABLE = "haul_top_up_unaffordable"
    HAUL_BUY_STILL_SHORT = "haul_buy_still_short"
    HAUL_UNRELATED_CARGO_LOADED = "haul_unrelated_cargo_loaded"
    ROUTE_UNCONFIRMED = "route_unconfirmed"
    BUYING_CARGO = "buying_cargo"
    SELLING_CARGO = "selling_cargo"
    SELLING_ALL_CARGO = "selling_all_cargo"
    SALE_PROFIT = "sale_profit"
    JUMP_INITIATED = "jump_initiated"
    ARRIVAL = "arrival"
    ARRIVAL_NEXT_STATION = "arrival_next_station"
    APPROACHING_STATION = "approaching_station"
    DOCKING_REQUEST = "docking_request"
    DOCKING_PAD_FULL = "docking_pad_full"
    AUTO_DOCKING_ENGAGED = "auto_docking_engaged"
    DOCKING_COMPLETE = "docking_complete"
    SHIP_SERVICED = "ship_serviced"
    UNDOCKING = "undocking"
    CARGO_LOADED = "cargo_loaded"
    ROUTE_COMPLETE = "route_complete"
    ROUTE_PROFIT_DELTA = "route_profit_delta"
    SESSION_COMPLETE = "session_complete"
    MARKET_LEVEL_LOW = "market_level_low"
    MARKET_BUY_NONE_AVAILABLE = "market_buy_none_available"
    SPANSH_ROUTE_READY = "spansh_route_ready"
    SPANSH_NEUTRON_WAYPOINT_SET = "spansh_neutron_waypoint_set"
    SPANSH_ROUTE_COMPLETE = "spansh_route_complete"


def parse_announcement_id(value: str) -> AnnouncementId | None:
    try:
        return AnnouncementId(value)
    except ValueError:
        return None


def format_credits_short(value: int) -> str:
    abs_value = abs(int(value))
    prefix = "-" if value < 0 else ""
    if abs_value >= 1_000_000_000:
        billions = abs_value // 1_000_000_000
        millions = (abs_value % 1_000_000_000) / 1_000_000
        return f"{prefix}{billions} billion {millions:.1f} million credits"
    if abs_value >= 1_000_000:
        amount = f"{abs_value / 1_000_000:.1f}".rstrip("0").rstrip(".")
        return f"{prefix}{amount} million credits"
    if abs_value >= 1_000:
        amount = int(round(abs_value / 1_000))
        return f"{prefix}{amount} thousand credits"
    return f"{value} credits"


_DIGIT_RUN_RE = re.compile(r"\d{3,}")
_SPOKEN_NAME_FIELDS = frozenset({"system_name", "station_name"})


def _spell_digit_runs(text: str) -> str:
    return _DIGIT_RUN_RE.sub(lambda match: " ".join(match.group(0)), text)


def normalize_tts_value(field_name: str, value: object) -> object:
    if field_name not in _SPOKEN_NAME_FIELDS or not isinstance(value, str):
        return value
    return _spell_digit_runs(value)


class SpeechBackend(Protocol):
    def speak(self, text: str) -> None: ...


class NullSpeechBackend:
    def speak(self, text: str) -> None:
        return None


@dataclass(frozen=True)
class CommandSpeechBackend:
    command_prefix: tuple[str, ...]

    def speak(self, text: str) -> None:
        subprocess.run([*self.command_prefix, text], check=False, capture_output=True)


@dataclass(frozen=True)
class PowerShellSpeechBackend:
    executable: str

    def speak(self, text: str) -> None:
        escaped = text.replace("'", "''")
        script = (
            "Add-Type -AssemblyName System.Speech; "
            "$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$speaker.Speak('{escaped}')"
        )
        subprocess.run(
            [self.executable, "-NoProfile", "-Command", script],
            check=False,
            capture_output=True,
        )


class PiperSpeechBackend:
    """Keeps one Piper (piper-tts) process loaded so each line skips the model load."""

    def __init__(
        self,
        voice: PiperVoiceConfig,
        *,
        start_process: Callable[[list[str]], subprocess.Popen[str]],
        play: Callable[[str], object],
    ) -> None:
        self._voice = voice
        self._start_process = start_process
        self._play = play
        self._output_dir = tempfile.mkdtemp(prefix="edcr-piper-")
        self._process: subprocess.Popen[str] | None = None
        # Held while speaking so a voice change lands between utterances.
        self._lock = Lock()

    @property
    def voice(self) -> PiperVoiceConfig:
        return self._voice

    def configure(self, voice: PiperVoiceConfig) -> None:
        with self._lock:
            self._voice = voice
            if self._process is not None:
                self._process.kill()
                self._process = None

    def speak(self, text: str) -> None:
        line = " ".join(text.split())
        if not line:
            return
        with self._lock:
            self._speak_line(line)

    def _speak_line(self, line: str) -> None:
        wav_path = self._synthesize(line) or self._synthesize(line)
        if not wav_path:
            return
        try:
            self._play(wav_path)
        finally:
            Path(wav_path).unlink(missing_ok=True)

    def _synthesize(self, line: str) -> str:
        if self._process is None or self._process.poll() is not None:
            self._process = self._start_process(piper_command(self._voice, output_dir=self._output_dir))
        # piper-tts reads one utterance per stdin line and logs `Wrote <path>` to stderr once the wav is complete.
        wav_path = ""
        try:
            assert self._process.stdin is not None and self._process.stderr is not None
            self._process.stdin.write(line + "\n")
            self._process.stdin.flush()
            while not wav_path:
                log_line = self._process.stderr.readline()
                if not log_line:
                    break
                _, marker, path = log_line.strip().partition("Wrote ")
                wav_path = path if marker else ""
        except OSError:
            wav_path = ""
        if not wav_path:
            # Dead Piper: drop it so the next attempt starts a fresh one.
            self._process.kill()
            self._process = None
        return wav_path


def piper_command(voice: PiperVoiceConfig, *, output_dir: str) -> list[str]:
    args = [str(voice.executable), "--model", str(voice.model)]
    for key in PIPER_TUNING_KEYS:
        value = getattr(voice, key)
        if value is not None:
            args += [f"--{key}", str(value)]
    return [*args, "--output_dir", output_dir]


# piper's own fallbacks when a model config or the command line leaves a value out.
_PIPER_BASE_DEFAULTS = {
    "length_scale": 1.0,
    "noise_scale": 0.667,
    "noise_w_scale": 0.8,
    "sentence_silence": 0.0,
    "volume": 1.0,
}


def piper_model_defaults(model: Path) -> dict[str, float]:
    """The values piper uses for unset tuning keys: the model's `inference` block, then piper's fallbacks."""
    defaults = dict(_PIPER_BASE_DEFAULTS)
    try:
        inference = json.loads(Path(f"{model}.json").read_text(encoding="utf-8")).get("inference", {})
    except (OSError, ValueError, AttributeError):
        return defaults
    for key, model_key in (("length_scale", "length_scale"), ("noise_scale", "noise_scale"), ("noise_w_scale", "noise_w")):
        value = inference.get(model_key) if isinstance(inference, dict) else None
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            defaults[key] = float(value)
    return defaults


def piper_voice_models(model: Path) -> tuple[Path, ...]:
    """Voices installed beside the configured one: `<voices>/<name>/<model>.onnx`."""
    voices_dir = model.parent.parent
    try:
        found = sorted(voices_dir.glob("*/*.onnx"))
    except OSError:
        found = []
    return tuple(found) if model in found else (model, *found)


_WAV_PLAYERS = {
    "linux": ("pw-play", "paplay", "aplay"),
    "macos": ("afplay",),
}


def _start_piper_process(args: list[str]) -> subprocess.Popen[str]:
    return subprocess.Popen(
        args,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        bufsize=1,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )


def _wav_player(platform_name: str) -> Callable[[str], object] | None:
    if platform_name == "windows":
        import winsound

        return lambda wav_path: winsound.PlaySound(wav_path, winsound.SND_FILENAME)
    player = next((name for name in _WAV_PLAYERS.get(platform_name, ()) if which(name)), None)
    if player is None:
        return None
    env = audio_env(os.environ, runtime_dir_exists=os.path.isdir) if platform_name == "linux" else None

    def play(wav_path: str) -> None:
        result = subprocess.run([player, wav_path], check=False, capture_output=True, text=True, env=env)
        if result.returncode != 0:
            logger.warning("TTS playback failed (%s exit %s): %s", player, result.returncode, result.stderr.strip())

    return play


def audio_env(environ: Mapping[str, str], *, runtime_dir_exists: Callable[[str], bool]) -> dict[str, str]:
    """PipeWire and PulseAudio clients find the sound server through XDG_RUNTIME_DIR, which
    processes started outside a login session (systemd-run scopes, some ssh/tmux setups) lack."""
    env = dict(environ)
    if not env.get("XDG_RUNTIME_DIR") and hasattr(os, "getuid"):
        runtime_dir = f"/run/user/{os.getuid()}"
        if runtime_dir_exists(runtime_dir):
            env["XDG_RUNTIME_DIR"] = runtime_dir
    return env


def build_speech_backend(platform_name: str, piper: PiperVoiceConfig | None) -> SpeechBackend:
    platform_name = platform_name.lower()
    if piper is not None and (play := _wav_player(platform_name)) is not None:
        return PiperSpeechBackend(piper, start_process=_start_piper_process, play=play)
    if platform_name == "macos" and which("say"):
        return CommandSpeechBackend(("say",))
    if platform_name == "linux":
        for name in ("spd-say", "espeak-ng", "espeak"):
            if which(name):
                return CommandSpeechBackend((name,))
    if platform_name == "windows":
        for executable in ("powershell", "pwsh"):
            if which(executable):
                return PowerShellSpeechBackend(executable)
    return NullSpeechBackend()


class QueuedSpeaker:
    def __init__(self, backend: SpeechBackend, *, max_backlog: int = 8) -> None:
        if max_backlog < 1:
            raise ValueError("QueuedSpeaker max_backlog must be at least 1.")
        self._backend = backend
        self._max_backlog = max_backlog
        self._pending: deque[_SpeechItem] = deque()
        self._condition = Condition()
        self._closed = False
        self._speaking = False
        self._thread = Thread(target=self._run, daemon=True)
        self._thread.start()

    def enqueue(self, text: str, *, collapse_key: object | None = None) -> None:
        item = _SpeechItem(text=text, collapse_key=collapse_key)
        with self._condition:
            if self._closed:
                return
            if (
                collapse_key is not None
                and self._speaking
                and any(queued.collapse_key == collapse_key for queued in self._pending)
            ):
                self._pending = deque(
                    queued for queued in self._pending if queued.collapse_key != collapse_key
                )
            while len(self._pending) >= self._max_backlog:
                self._pending.popleft()
            self._pending.append(item)
            self._condition.notify()

    def close(self) -> None:
        with self._condition:
            self._closed = True
            self._condition.notify_all()
        self._thread.join(timeout=1.0)

    def _run(self) -> None:
        while True:
            with self._condition:
                while not self._pending and not self._closed:
                    self._condition.wait(timeout=0.1)
                if not self._pending and self._closed:
                    return
                item = self._pending.popleft()
                self._speaking = True
            try:
                self._backend.speak(item.text)
            finally:
                with self._condition:
                    self._speaking = False


@dataclass(frozen=True)
class _SpeechItem:
    text: str
    collapse_key: object | None = None


class TTSAnnouncer:
    def __init__(
        self,
        config: TTSConfig,
        *,
        platform_name: str,
        backend: SpeechBackend | None = None,
    ) -> None:
        self.apply_wording(config)
        self._commander_name: str | None = None
        self._speaker: QueuedSpeaker | None = None
        self._last_text = ""
        selected_backend = backend if backend is not None else build_speech_backend(platform_name, config.piper)
        self._backend = selected_backend
        if config.enabled and not isinstance(selected_backend, NullSpeechBackend):
            self._speaker = QueuedSpeaker(selected_backend)

    @property
    def speech_on(self) -> bool:
        return self._speaker is not None

    @property
    def piper_voice(self) -> PiperVoiceConfig | None:
        """The live Piper voice, or None when speech runs through another backend."""
        return self._backend.voice if isinstance(self._backend, PiperSpeechBackend) else None

    def configure_piper(self, voice: PiperVoiceConfig) -> bool:
        if not isinstance(self._backend, PiperSpeechBackend):
            return False
        self._backend.configure(voice)
        return True

    def say(self, text: str) -> bool:
        """Speak free text now, skipping phrases and the disabled list. False when speech is off."""
        line = text.strip()
        if self._speaker is None or not line:
            return False
        self._speaker.enqueue(line)
        return True

    def phrase_presets(self) -> dict[str, str]:
        """Phrase templates with `{title}` filled in; other placeholders stay for the caller to fill."""
        title = self._resolve_title()
        return {
            message_id.value: template.replace("{title}", title)
            for message_id, template in self._phrases.items()
            if template.strip()
        }

    def apply_wording(self, config: TTSConfig) -> None:
        """Adopt title, phrase and disabled-message settings. The voice and on/off switch stay as built."""
        self._config = config
        self._disabled = {
            parsed
            for raw in config.disabled_messages
            if (parsed := parse_announcement_id(raw)) is not None
        }
        self._phrases = {
            parsed: text
            for raw, text in config.phrases.items()
            if (parsed := parse_announcement_id(raw)) is not None
        }

    def set_commander_name(self, name: str | None) -> None:
        text = str(name).strip() if name is not None else ""
        self._commander_name = text or None

    def render_announcement(self, message_id: AnnouncementId, /, **values: object) -> str | None:
        template = self._phrases.get(message_id)
        if not template:
            return None
        normalized_values = {
            key: normalize_tts_value(key, value)
            for key, value in values.items()
        }
        rendered = template.format(title=self._resolve_title(), **normalized_values).strip()
        if not rendered or rendered == self._last_text:
            return None
        return rendered

    def announce(self, message_id: AnnouncementId, /, **values: object) -> None:
        if self._speaker is None or message_id in self._disabled:
            return
        rendered = self.render_announcement(message_id, **values)
        if rendered is None:
            return
        self._last_text = rendered
        self._speaker.enqueue(rendered, collapse_key=message_id)

    def _resolve_title(self) -> str:
        if self._config.title_mode == "commander":
            return "commander"
        if self._config.title_mode == "commander_name":
            return self._commander_name or "commander"
        return self._config.title

    def close(self) -> None:
        if self._speaker is not None:
            self._speaker.close()
            self._speaker = None
