from __future__ import annotations

import io
import os
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from threading import Event
import unittest

from edcr.config import PiperVoiceConfig, TTSConfig
from edcr.tts import (
    AnnouncementId,
    PiperSpeechBackend,
    QueuedSpeaker,
    TTSAnnouncer,
    audio_env,
    format_credits_short,
    normalize_tts_value,
    piper_model_defaults,
    piper_voice_models,
)


class _FakeBackend:
    def __init__(self) -> None:
        self.spoken: list[str] = []

    def speak(self, text: str) -> None:
        self.spoken.append(text)


class _BlockingBackend:
    def __init__(self) -> None:
        self.spoken: list[str] = []
        self.started = Event()
        self.release = Event()

    def speak(self, text: str) -> None:
        self.spoken.append(text)
        if len(self.spoken) == 1:
            self.started.set()
            self.release.wait(timeout=1.0)


class _FakePiperProcess:
    """Writes one wav per stdin line and logs it like piper-tts; dies after `dies_after` lines."""

    def __init__(self, output_dir: str, *, dies_after: int | None = None) -> None:
        self.lines: list[str] = []
        self.killed = False
        self._output_dir = Path(output_dir)
        self._dies_after = dies_after
        self._pending_logs: list[str] = []
        self.stdin = self
        self.stderr = self

    def write(self, data: str) -> None:
        self.lines.append(data)
        if self._dies_after is not None and len(self.lines) > self._dies_after:
            return
        wav = self._output_dir / f"{len(self.lines)}.wav"
        wav.write_bytes(b"RIFF")
        self._pending_logs += ["WARNING:onnxruntime:noise\n", f"INFO:piper.__main__:Wrote {wav}\n"]

    def flush(self) -> None:
        return None

    def readline(self) -> str:
        return self._pending_logs.pop(0) if self._pending_logs else ""

    def poll(self) -> int | None:
        return -9 if self.killed else None

    def kill(self) -> None:
        self.killed = True


class PiperSpeechBackendTests(unittest.TestCase):
    def _backend(self, *, dies_after: int | None = None, voice: PiperVoiceConfig | None = None):
        started: list[list[str]] = []
        processes: list[_FakePiperProcess] = []
        played: list[str] = []

        def start_process(args: list[str]) -> _FakePiperProcess:
            started.append(args)
            # Only the first process misbehaves; a restarted Piper is healthy.
            processes.append(_FakePiperProcess(args[-1], dies_after=dies_after if not processes else None))
            return processes[-1]

        def play(wav_path: str) -> None:
            self.assertTrue(Path(wav_path).is_file())
            played.append(wav_path)

        backend = PiperSpeechBackend(
            voice or PiperVoiceConfig(executable=Path("piper"), model=Path("voice.onnx")),
            start_process=start_process,
            play=play,
        )
        self.addCleanup(shutil.rmtree, backend._output_dir, True)
        return backend, started, processes, played

    def test_keeps_one_process_and_plays_then_removes_each_wav(self) -> None:
        backend, started, processes, played = self._backend()

        backend.speak("Warning commander,\nwe are under attack.")
        backend.speak("Docking complete.")

        self.assertEqual(len(started), 1)
        self.assertEqual(started[0][:3], ["piper", "--model", "voice.onnx"])
        self.assertEqual(processes[0].lines, ["Warning commander, we are under attack.\n", "Docking complete.\n"])
        self.assertEqual(len(played), 2)
        self.assertFalse(any(Path(wav_path).exists() for wav_path in played))

    def test_restarts_piper_once_when_it_stops_answering(self) -> None:
        backend, started, processes, played = self._backend(dies_after=1)

        backend.speak("First.")
        backend.speak("Second.")

        self.assertEqual(len(started), 2)
        self.assertTrue(processes[0].killed)
        self.assertEqual(processes[1].lines, ["Second.\n"])
        self.assertEqual(len(played), 2)


    def test_passes_tuning_and_restarts_piper_with_a_new_voice(self) -> None:
        backend, started, processes, played = self._backend(
            voice=PiperVoiceConfig(executable=Path("piper"), model=Path("cori.onnx"), length_scale=0.9, volume=1.5),
        )

        backend.speak("First.")
        backend.configure(PiperVoiceConfig(executable=Path("piper"), model=Path("jenny.onnx"), noise_w_scale=0.5))
        backend.speak("Second.")

        self.assertEqual(started[0][:7], ["piper", "--model", "cori.onnx", "--length_scale", "0.9", "--volume", "1.5"])
        self.assertEqual(started[1][:5], ["piper", "--model", "jenny.onnx", "--noise_w_scale", "0.5"])
        self.assertTrue(processes[0].killed)
        self.assertEqual(backend.voice.model, Path("jenny.onnx"))
        self.assertEqual(len(played), 2)


class PiperVoiceFilesTests(unittest.TestCase):
    def test_reads_model_inference_defaults_and_lists_sibling_voices(self) -> None:
        with TemporaryDirectory() as temp_dir:
            voices = Path(temp_dir)
            cori = voices / "cori" / "en_GB-cori-high.onnx"
            jenny = voices / "jenny" / "en_GB-jenny_dioco-medium.onnx"
            for model in (cori, jenny):
                model.parent.mkdir()
                model.write_bytes(b"")
            Path(f"{cori}.json").write_text('{"inference": {"noise_scale": 0.5, "length_scale": 1.1, "noise_w": 0.7}}')

            self.assertEqual(
                piper_model_defaults(cori),
                {"length_scale": 1.1, "noise_scale": 0.5, "noise_w_scale": 0.7, "sentence_silence": 0.0, "volume": 1.0},
            )
            self.assertEqual(piper_model_defaults(jenny)["noise_scale"], 0.667)
            self.assertEqual(piper_voice_models(cori), (cori, jenny))


@unittest.skipUnless(hasattr(os, "getuid"), "XDG_RUNTIME_DIR is a POSIX session concept")
class AudioEnvTests(unittest.TestCase):
    def test_fills_missing_runtime_dir_so_pipewire_is_reachable(self) -> None:
        runtime_dir = f"/run/user/{os.getuid()}"

        env = audio_env({"PATH": "/usr/bin"}, runtime_dir_exists=lambda path: path == runtime_dir)

        self.assertEqual(env, {"PATH": "/usr/bin", "XDG_RUNTIME_DIR": runtime_dir})

    def test_keeps_an_existing_runtime_dir_and_skips_a_missing_one(self) -> None:
        self.assertEqual(
            audio_env({"XDG_RUNTIME_DIR": "/custom"}, runtime_dir_exists=lambda _: True),
            {"XDG_RUNTIME_DIR": "/custom"},
        )
        self.assertEqual(audio_env({}, runtime_dir_exists=lambda _: False), {})


class TTSHelpersTests(unittest.TestCase):
    def test_queued_speaker_coalesces_stale_pending_items_with_same_key(self) -> None:
        backend = _BlockingBackend()
        speaker = QueuedSpeaker(backend, max_backlog=4)
        self.addCleanup(speaker.close)

        speaker.enqueue("First item")
        self.assertTrue(backend.started.wait(timeout=1.0))

        speaker.enqueue("Route update one", collapse_key=AnnouncementId.DESTINATION_SET)
        speaker.enqueue("Route update two", collapse_key=AnnouncementId.DESTINATION_SET)
        speaker.enqueue("Route update three", collapse_key=AnnouncementId.DESTINATION_SET)

        backend.release.set()
        speaker.close()

        self.assertEqual(backend.spoken, ["First item", "Route update three"])

    def test_queued_speaker_drops_oldest_pending_items_when_backlog_is_full(self) -> None:
        backend = _BlockingBackend()
        speaker = QueuedSpeaker(backend, max_backlog=2)
        self.addCleanup(speaker.close)

        speaker.enqueue("First item")
        self.assertTrue(backend.started.wait(timeout=1.0))

        speaker.enqueue("Second item")
        speaker.enqueue("Third item")
        speaker.enqueue("Fourth item")

        backend.release.set()
        speaker.close()

        self.assertEqual(backend.spoken, ["First item", "Third item", "Fourth item"])

    def test_format_credits_short_humanizes_thousands_and_millions(self) -> None:
        self.assertEqual(format_credits_short(84_200), "84 thousand credits")
        self.assertEqual(format_credits_short(1_250_000), "1.2 million credits")
        self.assertEqual(
            format_credits_short(1_234_567_890),
            "1 billion 234.6 million credits",
        )

    def test_normalize_tts_value_spells_three_plus_digits_in_system_and_station_names(self) -> None:
        self.assertEqual(normalize_tts_value("system_name", "HIP 58412"), "HIP 5 8 4 1 2")
        self.assertEqual(normalize_tts_value("station_name", "Pier 2064"), "Pier 2 0 6 4")
        self.assertEqual(normalize_tts_value("system_name", "B13-2"), "B13-2")
        self.assertEqual(normalize_tts_value("system_name", "B100 32-1"), "B1 0 0 32-1")
        self.assertEqual(normalize_tts_value("commodity_name", "Aluminium 2064"), "Aluminium 2064")

    def test_announcer_uses_enum_and_respects_disabled_messages(self) -> None:
        backend = _FakeBackend()
        announcer = TTSAnnouncer(
            TTSConfig(
                enabled=True,
                title_mode="custom",
                title="captain",
                disabled_messages=("arrival",),
                phrases={
                    "arrival": "We are dropping out of hyper space jump captain.",
                    "station_cleared": "Ready to jump, {title}.",
                    "haul_aborted": "Haul aborted.",
                },
            ),
            platform_name="macos",
            backend=backend,
        )
        self.addCleanup(announcer.close)

        announcer.announce(AnnouncementId.ARRIVAL, system_name="Achenar")
        announcer.announce(AnnouncementId.STATION_CLEARED)
        announcer.announce(AnnouncementId.HAUL_ABORTED)
        announcer.close()

        self.assertEqual(backend.spoken, ["Ready to jump, captain.", "Haul aborted."])
        # Rendering is what gets published to pages and the hub, so a disabled message is never published.
        self.assertIsNone(announcer.render_announcement(AnnouncementId.ARRIVAL, system_name="Achenar"))
        self.assertEqual(announcer.render_announcement(AnnouncementId.STATION_CLEARED), "Ready to jump, captain.")

    def test_announcer_says_free_text_and_offers_phrase_presets(self) -> None:
        backend = _FakeBackend()
        announcer = TTSAnnouncer(
            TTSConfig(
                title_mode="custom",
                title="captain",
                disabled_messages=("haul_aborted",),
                phrases={"haul_aborted": "Haul aborted, {title}.", "arrival": "Arrived at {system_name}."},
            ),
            platform_name="macos",
            backend=backend,
        )
        self.addCleanup(announcer.close)

        self.assertTrue(announcer.say("  Fly safe, commander. "))
        self.assertFalse(announcer.say("   "))
        announcer.close()

        self.assertEqual(backend.spoken, ["Fly safe, commander."])
        self.assertEqual(
            announcer.phrase_presets(),
            {"haul_aborted": "Haul aborted, captain.", "arrival": "Arrived at {system_name}."},
        )
        self.assertIsNone(announcer.piper_voice)
        self.assertFalse(announcer.configure_piper(PiperVoiceConfig(executable=Path("piper"), model=Path("v.onnx"))))

    def test_a_muted_announcer_skips_callouts_but_still_says_free_text(self) -> None:
        backend = _FakeBackend()
        announcer = TTSAnnouncer(
            TTSConfig(phrases={"arrival": "Arrived at {system_name}.", "undocking": "Undocking."}),
            platform_name="macos",
            backend=backend,
        )
        self.addCleanup(announcer.close)

        announcer.muted = True
        announcer.announce(AnnouncementId.ARRIVAL, system_name="Sol")
        announcer.say("A line from the hub.")
        announcer.muted = False
        announcer.announce(AnnouncementId.UNDOCKING)
        announcer.close()

        self.assertEqual(backend.spoken, ["A line from the hub.", "Undocking."])

    def test_announcer_renders_market_level_low_phrase(self) -> None:
        backend = _FakeBackend()
        announcer = TTSAnnouncer(
            TTSConfig(
                enabled=True,
                title_mode="custom",
                title="captain",
                disabled_messages=(),
                phrases={
                    "market_level_low": "Station {market_side} for {commodity_name} is low at {units} units.",
                },
            ),
            platform_name="macos",
            backend=backend,
        )
        self.addCleanup(announcer.close)

        announcer.announce(
            AnnouncementId.MARKET_LEVEL_LOW,
            market_side="demand",
            commodity_name="Aluminium",
            units=200,
        )
        announcer.close()

        self.assertEqual(backend.spoken, ["Station demand for Aluminium is low at 200 units."])

    def test_announcer_spells_long_digits_in_system_names(self) -> None:
        backend = _FakeBackend()
        announcer = TTSAnnouncer(
            TTSConfig(
                enabled=True,
                title_mode="custom",
                title="captain",
                disabled_messages=(),
                phrases={
                    "destination_set": "Setting destination to {system_name}.",
                },
            ),
            platform_name="macos",
            backend=backend,
        )
        self.addCleanup(announcer.close)

        announcer.announce(AnnouncementId.DESTINATION_SET, system_name="HIP 58412")
        announcer.close()

        self.assertEqual(backend.spoken, ["Setting destination to HIP 5 8 4 1 2."])

    def test_announcer_renders_ship_serviced_phrase_with_title(self) -> None:
        backend = _FakeBackend()
        announcer = TTSAnnouncer(
            TTSConfig(
                enabled=True,
                title_mode="custom",
                title="captain",
                disabled_messages=(),
                phrases={
                    "ship_serviced": "Ship is fully fueled up and repaired, {title}.",
                },
            ),
            platform_name="macos",
            backend=backend,
        )
        self.addCleanup(announcer.close)

        announcer.announce(AnnouncementId.SHIP_SERVICED)
        announcer.close()

        self.assertEqual(backend.spoken, ["Ship is fully fueled up and repaired, captain."])

    def test_announcer_renders_auto_docking_phrase(self) -> None:
        backend = _FakeBackend()
        announcer = TTSAnnouncer(
            TTSConfig(
                enabled=True,
                title_mode="custom",
                title="captain",
                disabled_messages=(),
                phrases={
                    "auto_docking_engaged": "Engaging auto docking sequence.",
                },
            ),
            platform_name="macos",
            backend=backend,
        )
        self.addCleanup(announcer.close)

        announcer.announce(AnnouncementId.AUTO_DOCKING_ENGAGED)
        announcer.close()

        self.assertEqual(backend.spoken, ["Engaging auto docking sequence."])

    def test_announcer_uses_literal_commander_title_mode(self) -> None:
        backend = _FakeBackend()
        announcer = TTSAnnouncer(
            TTSConfig(
                enabled=True,
                title_mode="commander",
                title="captain",
                disabled_messages=(),
                phrases={
                    "station_cleared": "Ready to jump, {title}.",
                },
            ),
            platform_name="macos",
            backend=backend,
        )
        self.addCleanup(announcer.close)

        announcer.set_commander_name("VRYAE")
        announcer.announce(AnnouncementId.STATION_CLEARED)
        announcer.close()

        self.assertEqual(backend.spoken, ["Ready to jump, commander."])

    def test_announcer_uses_detected_commander_name_title_mode(self) -> None:
        backend = _FakeBackend()
        announcer = TTSAnnouncer(
            TTSConfig(
                enabled=True,
                title_mode="commander_name",
                title="captain",
                disabled_messages=(),
                phrases={
                    "station_cleared": "Ready to jump, {title}.",
                },
            ),
            platform_name="macos",
            backend=backend,
        )
        self.addCleanup(announcer.close)

        announcer.announce(AnnouncementId.STATION_CLEARED)
        announcer.set_commander_name("VRYAE")
        announcer.announce(AnnouncementId.STATION_CLEARED)
        announcer.close()

        self.assertEqual(
            backend.spoken,
            ["Ready to jump, commander.", "Ready to jump, VRYAE."],
        )

    def test_announcer_coalesces_stale_destination_updates(self) -> None:
        backend = _BlockingBackend()
        announcer = TTSAnnouncer(
            TTSConfig(
                enabled=True,
                title_mode="custom",
                title="captain",
                disabled_messages=(),
                phrases={
                    "station_cleared": "Ready to jump, {title}.",
                    "destination_set": "Setting destination to {system_name}.",
                },
            ),
            platform_name="macos",
            backend=backend,
        )
        self.addCleanup(announcer.close)

        announcer.announce(AnnouncementId.STATION_CLEARED)
        self.assertTrue(backend.started.wait(timeout=1.0))

        announcer.announce(AnnouncementId.DESTINATION_SET, system_name="Achenar")
        announcer.announce(AnnouncementId.DESTINATION_SET, system_name="Alioth")
        announcer.announce(AnnouncementId.DESTINATION_SET, system_name="HIP 58412")

        backend.release.set()
        announcer.close()

        self.assertEqual(
            backend.spoken,
            ["Ready to jump, captain.", "Setting destination to HIP 5 8 4 1 2."],
        )
