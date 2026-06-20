from __future__ import annotations

import unittest
from unittest.mock import patch

from tools import speak
from edap.config import ConfigError
from edap.tts import NullSpeechBackend


class _FakeBackend:
    def __init__(self) -> None:
        self.spoken: list[str] = []

    def speak(self, text: str) -> None:
        self.spoken.append(text)


class SpeakScriptTests(unittest.TestCase):
    def test_main_uses_detected_platform_backend_and_joins_text(self) -> None:
        backend = _FakeBackend()

        with (
            patch("tools.speak.default_runtime_platform", return_value="linux") as detect_platform,
            patch("tools.speak.build_speech_backend", return_value=backend) as build_backend,
        ):
            result = speak.main(["hello", "there"])

        self.assertEqual(result, 0)
        detect_platform.assert_called_once_with()
        build_backend.assert_called_once_with("linux")
        self.assertEqual(backend.spoken, ["hello there"])

    def test_main_can_normalize_system_name_text(self) -> None:
        backend = _FakeBackend()

        with (
            patch("tools.speak.default_runtime_platform", return_value="linux"),
            patch("tools.speak.build_speech_backend", return_value=backend),
        ):
            result = speak.main(["--system-name", "HIP", "58412"])

        self.assertEqual(result, 0)
        self.assertEqual(backend.spoken, ["HIP 5 8 4 1 2"])

    def test_main_can_normalize_station_name_text(self) -> None:
        backend = _FakeBackend()

        with (
            patch("tools.speak.default_runtime_platform", return_value="linux"),
            patch("tools.speak.build_speech_backend", return_value=backend),
        ):
            result = speak.main(["--station-name", "Pier", "2064"])

        self.assertEqual(result, 0)
        self.assertEqual(backend.spoken, ["Pier 2 0 6 4"])

    def test_main_returns_error_when_platform_detection_requires_explicit_config(self) -> None:
        with patch(
            "tools.speak.default_runtime_platform",
            side_effect=ConfigError("runtime platform must be set explicitly"),
        ):
            with patch("sys.stderr") as stderr:
                result = speak.main(["hello"])

        self.assertEqual(result, 2)
        stderr.write.assert_called_with("runtime platform must be set explicitly\n")

    def test_main_returns_error_when_no_backend_is_available(self) -> None:
        with (
            patch("tools.speak.default_runtime_platform", return_value="linux"),
            patch("tools.speak.build_speech_backend", return_value=NullSpeechBackend()),
        ):
            with patch("sys.stderr") as stderr:
                result = speak.main(["hello"])

        self.assertEqual(result, 2)
        stderr.write.assert_called_with("No TTS backend available for detected platform: linux\n")
