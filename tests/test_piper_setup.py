from __future__ import annotations

import hashlib
import tempfile
import tomllib
import unittest
from pathlib import Path

from edcr.piper_setup import (
    VOICES,
    PiperVoice,
    VoiceFile,
    install_voice,
    piper_data_dir,
    piper_executable,
    with_piper_config,
)

_MODEL = b"onnx-bytes"
_VOICE = PiperVoice(
    key="test",
    label="Test",
    url_dir="en/en_GB/test/medium",
    files=(VoiceFile("test.onnx", len(_MODEL), hashlib.md5(_MODEL).hexdigest()),),
)


class PiperSetupTests(unittest.TestCase):
    def test_default_voices_credit_jenny_as_her_license_asks(self) -> None:
        self.assertEqual(VOICES["cori"].model_name, "en_GB-cori-high.onnx")
        self.assertIn("Jenny (Dioco)", VOICES["jenny"].label)

    def test_data_dir_follows_each_platform_convention(self) -> None:
        home = Path("home")
        self.assertEqual(
            piper_data_dir("macos", home=home, env={}),
            home / "Library" / "Application Support" / "EDControlRoom" / "piper",
        )
        self.assertEqual(
            piper_data_dir("windows", home=home, env={"LOCALAPPDATA": "appdata"}),
            Path("appdata") / "EDControlRoom" / "piper",
        )
        self.assertEqual(piper_data_dir("linux", home=home, env={}), home / ".local" / "share" / "EDControlRoom" / "piper")
        self.assertEqual(piper_data_dir("linux", home=home, env={"XDG_DATA_HOME": "xdg"}), Path("xdg") / "EDControlRoom" / "piper")
        self.assertEqual(piper_executable(Path("bin"), "windows"), Path("bin") / "piper.exe")
        self.assertEqual(piper_executable(Path("bin"), "linux"), Path("bin") / "piper")

    def test_install_voice_downloads_once_and_rejects_corrupt_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fetched: list[str] = []

            def fetch(url: str):
                fetched.append(url)
                return [_MODEL[:4], _MODEL[4:]]

            model = install_voice(_VOICE, Path(temp_dir), fetch=fetch, progress=lambda _: None)
            install_voice(_VOICE, Path(temp_dir), fetch=fetch, progress=lambda _: None)

            self.assertEqual(model.read_bytes(), _MODEL)
            self.assertEqual(fetched, ["https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/test/medium/test.onnx"])

            model.write_bytes(b"truncated")
            with self.assertRaisesRegex(ValueError, "checksum"):
                install_voice(_VOICE, Path(temp_dir), fetch=lambda _: [b"garbage"], progress=lambda _: None)
            self.assertEqual(model.read_bytes(), b"truncated")
            self.assertEqual(sorted(path.name for path in model.parent.iterdir()), ["test.onnx"])

    def test_piper_config_is_appended_or_replaced_in_place(self) -> None:
        executable = Path("bin") / "piper"
        model = Path("voices") / "cori.onnx"
        expected = f"[tts.piper]\nexecutable = '{executable}'\nmodel = '{model}'\n"

        self.assertEqual(with_piper_config("", executable=executable, model=model), expected)
        self.assertEqual(
            with_piper_config('[tts]\ntitle_mode = "commander_name"\n', executable=executable, model=model),
            f'[tts]\ntitle_mode = "commander_name"\n\n{expected}',
        )
        existing = "[tts.piper]\n# old voice\nexecutable = 'old'\nmodel = 'old.onnx'\n\n[timing]\nenabled = true\n"
        self.assertEqual(
            with_piper_config(existing, executable=executable, model=model),
            f"{expected}\n[timing]\nenabled = true\n",
        )

    def test_windows_paths_stay_literal_in_toml(self) -> None:
        text = with_piper_config("", executable=Path("C:\\Users\\cmdr\\piper.exe"), model=Path("C:\\voices\\cori.onnx"))

        self.assertEqual(tomllib.loads(text)["tts"]["piper"]["executable"], "C:\\Users\\cmdr\\piper.exe")
