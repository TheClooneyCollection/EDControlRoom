"""Install piper-tts and an EDControlRoom default voice, then point `[tts.piper]` at them."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Mapping

# Pinned so a piper-tts CLI change cannot silently break `PiperSpeechBackend`.
PIPER_TTS_PACKAGE = "piper-tts==1.8.0"
VOICES_BASE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"


@dataclass(frozen=True)
class VoiceFile:
    name: str
    size_bytes: int
    md5_digest: str


@dataclass(frozen=True)
class PiperVoice:
    key: str
    # Shown to players; Jenny's dataset license asks for "Jenny (Dioco)" wherever practical.
    label: str
    url_dir: str
    files: tuple[VoiceFile, ...]

    @property
    def model_name(self) -> str:
        return self.files[0].name


# Sizes and digests from piper-voices v1.0.0 `voices.json`.
VOICES: dict[str, PiperVoice] = {
    "cori": PiperVoice(
        key="cori",
        label="Cori (en_GB, high quality)",
        url_dir="en/en_GB/cori/high",
        files=(
            VoiceFile("en_GB-cori-high.onnx", 114_219_352, "3474a80133d9a03e6870d2ac42c18806"),
            VoiceFile("en_GB-cori-high.onnx.json", 4_963, "0f7d42e77a99193006aa34a34442f5e0"),
            VoiceFile("MODEL_CARD", 468, "12db31ecedf1d6458a215d3012339a20"),
        ),
    ),
    "jenny": PiperVoice(
        key="jenny",
        label="Jenny (Dioco) (en_GB, medium quality)",
        url_dir="en/en_GB/jenny_dioco/medium",
        files=(
            VoiceFile("en_GB-jenny_dioco-medium.onnx", 63_201_294, "d08f2f7edf0c858275a7eca74ff2a9e4"),
            VoiceFile("en_GB-jenny_dioco-medium.onnx.json", 4_895, "e999a9c0aa535fb42e43b04cebcd65d2"),
            VoiceFile("MODEL_CARD", 298, "ff351d05502764d5b4a074e0648e9434"),
        ),
    ),
}
DEFAULT_VOICE = "cori"


def piper_data_dir(platform_name: str, *, home: Path, env: Mapping[str, str]) -> Path:
    if platform_name == "macos":
        return home / "Library" / "Application Support" / "EDControlRoom" / "piper"
    if platform_name == "windows":
        local_app_data = env.get("LOCALAPPDATA")
        base = Path(local_app_data) if local_app_data else home / "AppData" / "Local"
        return base / "EDControlRoom" / "piper"
    data_home = env.get("XDG_DATA_HOME")
    return (Path(data_home) if data_home else home / ".local" / "share") / "EDControlRoom" / "piper"


def piper_executable(tool_bin_dir: Path, platform_name: str) -> Path:
    return tool_bin_dir / ("piper.exe" if platform_name == "windows" else "piper")


def install_voice(
    voice: PiperVoice,
    voices_dir: Path,
    *,
    fetch: Callable[[str], Iterable[bytes]],
    progress: Callable[[str], None],
) -> Path:
    """Download each voice file unless an intact copy is already there. Returns the model path."""
    voice_dir = voices_dir / voice.key
    voice_dir.mkdir(parents=True, exist_ok=True)
    for voice_file in voice.files:
        target = voice_dir / voice_file.name
        if target.is_file() and _file_md5(target) == voice_file.md5_digest:
            progress(f"  {voice_file.name}: already installed")
            continue
        progress(f"  {voice_file.name}: downloading {voice_file.size_bytes / 1_000_000:.1f} MB")
        partial = target.with_name(target.name + ".part")
        digest = hashlib.md5()
        with partial.open("wb") as handle:
            for chunk in fetch(f"{VOICES_BASE_URL}/{voice.url_dir}/{voice_file.name}"):
                digest.update(chunk)
                handle.write(chunk)
        if digest.hexdigest() != voice_file.md5_digest:
            partial.unlink()
            raise ValueError(f"{voice_file.name} failed its checksum; nothing was installed.")
        partial.replace(target)
    return voice_dir / voice.model_name


_PIPER_SECTION = re.compile(r"^\[tts\.piper\][^\n]*\n(?:(?!\[)[^\n]*\n?)*", re.MULTILINE)


def with_piper_config(config_text: str, *, executable: Path, model: Path) -> str:
    """Replace or append `[tts.piper]`, keeping the rest of config.toml as written."""
    # TOML literal strings so Windows backslashes are not read as escapes.
    section = f"[tts.piper]\nexecutable = '{executable}'\nmodel = '{model}'\n"
    if _PIPER_SECTION.search(config_text):
        return _PIPER_SECTION.sub(lambda _: section + "\n", config_text, count=1).rstrip("\n") + "\n"
    prefix = config_text.rstrip("\n")
    return f"{prefix}\n\n{section}" if prefix else section


def _file_md5(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "md5").hexdigest()
