from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from edcr.config import ConfigError, InputConfig, load_config
from edcr.platform.input.factory import build_input_controller
from edcr.platform.input.linux import LinuxInputController
from edcr.platform.input.uinput import LinuxUinputController, evdev_code
from edcr.timing import TimingChannelConfig, TimingConfig, TimingSampler, no_jitter_timing_sampler


def unexpected(*args, **kwargs):
    raise AssertionError("Unexpected uinput dependency used")


class FakeKeyboard:
    """Records what reached the virtual keyboard, interleaved with sleeps."""

    def __init__(self) -> None:
        self.events: list[tuple[str, object]] = []

    def write_key(self, code: int, down: bool) -> None:
        self.events.append(("down" if down else "up", code))

    def sleep(self, duration: float) -> None:
        self.events.append(("sleep", duration))

    def close(self) -> None:
        self.events.append(("close", None))


def controller(*, write_key=unexpected, close_device=unexpected, sleeper=unexpected,
               timing_sampler: TimingSampler = no_jitter_timing_sampler()) -> LinuxUinputController:
    return LinuxUinputController(write_key=write_key, close_device=close_device, sleeper=sleeper, timing_sampler=timing_sampler)


def recording() -> tuple[LinuxUinputController, FakeKeyboard]:
    keyboard = FakeKeyboard()
    return controller(write_key=keyboard.write_key, close_device=keyboard.close, sleeper=keyboard.sleep), keyboard


class EvdevCodeTests(unittest.TestCase):
    def test_internal_key_names_map_to_linux_evdev_codes(self) -> None:
        cases = {
            "escape": 1, "1": 2, "a": 30, "m": 50, ",": 51, ".": 52, "[": 26, "]": 27,
            "left_shift": 42, "left_control": 29, "space": 57, "f1": 59, "f12": 88, "f13": 183, "f15": 185,
            "numpad_3": 81, "numpad_enter": 96, "right_control": 97, "numpad_divide": 98, "right_alt": 100,
            "home": 102, "up": 103, "left": 105, "right": 106, "down": 108, "delete": 111, "left_command": 125,
        }
        for key, code in cases.items():
            with self.subTest(key=key):
                self.assertEqual(evdev_code(key), code)

    def test_modifier_aliases_resolve_to_left_hand_keys(self) -> None:
        for modifier, code in {"ctrl": 29, "shift": 42, "alt": 56, "right_alt": 100}.items():
            with self.subTest(modifier=modifier):
                self.assertEqual(evdev_code(modifier, modifier=True), code)


class LinuxUinputControllerTests(unittest.TestCase):
    def test_galaxy_map_chord_holds_ctrl_around_m_for_the_sampled_hold(self) -> None:
        driver, keyboard = recording()

        driver.tap_key("m", modifier="ctrl", hold_s=0.1)

        self.assertEqual(keyboard.events, [("down", 29), ("down", 50), ("sleep", 0.1), ("up", 50), ("up", 29)])

    def test_held_key_stays_down_until_released(self) -> None:
        driver, keyboard = recording()

        driver.press_key("up")
        driver.release_key("up")

        self.assertEqual(keyboard.events, [("down", 103), ("up", 103)])

    def test_hold_and_typing_delays_go_through_the_timing_sampler(self) -> None:
        keyboard = FakeKeyboard()
        sampler = TimingSampler(
            TimingConfig(
                enabled=True,
                distribution="log_normal",
                delay=TimingChannelConfig(sigma=0.0, min_factor=1.0, max_factor=1.0),
                hold=TimingChannelConfig(sigma=0.0, min_factor=1.0, max_factor=1.0, min_seconds=0.04),
                typing=TimingChannelConfig(sigma=0.0, min_factor=1.0, max_factor=1.0, min_seconds=0.03),
            )
        )
        driver = controller(write_key=keyboard.write_key, sleeper=keyboard.sleep, timing_sampler=sampler)

        driver.tap_key("a", hold_s=0.01)
        driver.type_text("a", char_delay_s=0.01)

        self.assertEqual(keyboard.events, [("down", 30), ("sleep", 0.04), ("up", 30), ("down", 30), ("up", 30), ("sleep", 0.03)])

    def test_typing_a_system_name_shifts_capitals_and_symbols(self) -> None:
        driver, keyboard = recording()

        driver.type_text("Sol 1!", char_delay_s=0)

        self.assertEqual(
            keyboard.events,
            [
                ("down", 42), ("down", 31), ("up", 31), ("up", 42),
                ("down", 24), ("up", 24),
                ("down", 38), ("up", 38),
                ("down", 57), ("up", 57),
                ("down", 2), ("up", 2),
                ("down", 42), ("down", 2), ("up", 2), ("up", 42),
            ],
        )

    def test_unsupported_input_fails_before_anything_reaches_the_keyboard(self) -> None:
        driver = controller()

        with self.assertRaisesRegex(ValueError, "Unsupported key"):
            driver.tap_key("not_a_key")
        with self.assertRaisesRegex(ValueError, "Unsupported modifier"):
            driver.tap_key("a", modifier="hyper")
        with self.assertRaisesRegex(ValueError, "Unsupported character"):
            driver.type_text("é", char_delay_s=0)

    def test_targets_the_foreground_window_and_closing_destroys_the_device(self) -> None:
        driver, keyboard = recording()

        self.assertEqual(driver.set_foreground_target().summary(), "foreground window")
        self.assertEqual(driver.input_status(), {"target": "foreground window", "backend": "uinput"})
        driver.close()

        self.assertEqual(keyboard.events, [("close", None)])


class LinuxBackendSelectionTests(unittest.TestCase):
    def test_linux_defaults_to_uinput_without_creating_the_device(self) -> None:
        built = build_input_controller("linux", input_config=InputConfig(), timing_sampler=no_jitter_timing_sampler())

        self.assertIsInstance(built, LinuxUinputController)
        built.close()

    def test_xdotool_backend_stays_selectable(self) -> None:
        built = build_input_controller(
            "linux", input_config=InputConfig(linux_backend="xdotool"), timing_sampler=no_jitter_timing_sampler()
        )

        self.assertIsInstance(built, LinuxInputController)

    def test_config_reads_and_validates_the_linux_backend(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text("[input.linux]\nbackend = 'xdotool'\n", encoding="utf-8")
            self.assertEqual(load_config(path).input.linux_backend, "xdotool")

            path.write_text("[input.linux]\nbackend = 'ydotool'\n", encoding="utf-8")
            with self.assertRaisesRegex(ConfigError, "input.linux.backend"):
                load_config(path)


if __name__ == "__main__":
    unittest.main()
