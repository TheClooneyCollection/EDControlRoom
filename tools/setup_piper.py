from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import httpx

from edap.config import DEFAULT_CONFIG_PATH, ConfigError, PiperVoiceConfig, default_runtime_platform, load_config
from edap.piper_setup import (
    DEFAULT_VOICE,
    PIPER_TTS_PACKAGE,
    VOICES,
    install_voice,
    piper_data_dir,
    piper_executable,
    with_piper_config,
)
from edap.tts import PiperSpeechBackend, build_speech_backend


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Install the Piper TTS engine (piper-tts, via `uv tool`) and an EDControlRoom voice, "
            "then point [tts.piper] in config.toml at them."
        )
    )
    parser.add_argument("--voice", choices=sorted(VOICES), default=DEFAULT_VOICE, help=f"Voice to install (default: {DEFAULT_VOICE})")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Config TOML file to update")
    args = parser.parse_args(argv)

    try:
        platform_name = default_runtime_platform()
    except ConfigError as exc:
        sys.stderr.write(f"{exc}\n")
        return 2
    if shutil.which("uv") is None:
        sys.stderr.write("`uv` is not on PATH; install it first (https://docs.astral.sh/uv/).\n")
        return 2

    print(f"Installing {PIPER_TTS_PACKAGE} with `uv tool install`...")
    install = subprocess.run(["uv", "tool", "install", PIPER_TTS_PACKAGE], capture_output=True, text=True)
    if install.returncode != 0:
        sys.stderr.write(install.stderr)
        return 1
    tool_bin_dir = Path(subprocess.run(["uv", "tool", "dir", "--bin"], capture_output=True, text=True, check=True).stdout.strip())
    executable = piper_executable(tool_bin_dir, platform_name)
    if not executable.is_file():
        sys.stderr.write(f"piper-tts installed, but {executable} is missing.\n")
        return 1

    voice = VOICES[args.voice]
    voices_dir = piper_data_dir(platform_name, home=Path.home(), env=os.environ) / "voices"
    print(f"Installing voice {voice.label} into {voices_dir}")
    try:
        model = install_voice(voice, voices_dir, fetch=_fetch, progress=print)
    except (httpx.HTTPError, ValueError) as exc:
        sys.stderr.write(f"Voice download failed: {exc}\n")
        return 1

    config_path = Path(args.config)
    previous = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    config_path.write_text(with_piper_config(previous, executable=executable, model=model), encoding="utf-8")
    try:
        load_config(config_path)
    except ConfigError as exc:
        config_path.write_text(previous, encoding="utf-8")
        sys.stderr.write(f"Updated config did not load, restored it: {exc}\n")
        return 1
    print(f"Updated [tts.piper] in {config_path}")

    backend = build_speech_backend(platform_name, PiperVoiceConfig(executable=executable, model=model))
    if not isinstance(backend, PiperSpeechBackend):
        print("No audio player found for Piper on this platform; EDControlRoom will keep the platform voice.")
        return 0
    print("Speaking a test line...")
    backend.speak("Piper voice ready, commander.")
    print("Done. Restart Control Room to use the new voice.")
    return 0


def _fetch(url: str):
    with httpx.stream("GET", url, follow_redirects=True, timeout=60.0) as response:
        response.raise_for_status()
        yield from response.iter_bytes(chunk_size=1 << 20)


if __name__ == "__main__":
    raise SystemExit(main())
