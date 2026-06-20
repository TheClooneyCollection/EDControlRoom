from __future__ import annotations

import argparse
import sys

from edap.config import ConfigError, default_runtime_platform
from edap.tts import NullSpeechBackend, build_speech_backend, normalize_tts_value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Speak a short message through EDControlRoom TTS")
    name_group = parser.add_mutually_exclusive_group()
    name_group.add_argument(
        "--system-name",
        action="store_true",
        help="Normalize the text like a spoken system name before speaking it.",
    )
    name_group.add_argument(
        "--station-name",
        action="store_true",
        help="Normalize the text like a spoken station name before speaking it.",
    )
    parser.add_argument("text", nargs="+", help="Text to speak")
    args = parser.parse_args(argv)

    try:
        platform_name = default_runtime_platform()
    except ConfigError as exc:
        sys.stderr.write(f"{exc}\n")
        return 2

    backend = build_speech_backend(platform_name)
    if isinstance(backend, NullSpeechBackend):
        sys.stderr.write(f"No TTS backend available for detected platform: {platform_name}\n")
        return 2

    field_name = "text"
    if args.system_name:
        field_name = "system_name"
    elif args.station_name:
        field_name = "station_name"
    spoken_text = str(normalize_tts_value(field_name, " ".join(args.text)))
    backend.speak(spoken_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
