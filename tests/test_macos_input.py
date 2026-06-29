from __future__ import annotations

import unittest

from edap.platform.input.macos import (
    KEY_CODES,
    MODIFIER_FLAGS,
    MacOSInputController,
    _find_pid_in_ps_output,
)
from edap.timing import TimingChannelConfig, TimingConfig, TimingSampler, no_jitter_timing_sampler


class FakeBackend:
    def __init__(self) -> None:
        self.events: list[tuple] = []

    def post(self, keycode: int, down: bool, flags: int, unicode_char: str | None) -> None:
        self.events.append(("down" if down else "up", keycode, flags, unicode_char))

    def post_to_pid(self, pid: int, keycode: int, down: bool, flags: int, unicode_char: str | None) -> None:
        self.events.append(("pid", pid, "down" if down else "up", keycode, flags, unicode_char))

    def sleep(self, duration: float) -> None:
        self.events.append(("sleep", duration))


def _build() -> tuple[MacOSInputController, FakeBackend]:
    backend = FakeBackend()
    return (
        MacOSInputController(
            poster=backend.post,
            pid_poster=backend.post_to_pid,
            pid_finder=lambda process_name: 4242 if process_name == "EliteDangerous64.exe" else None,
            sleeper=backend.sleep,
            timing_sampler=no_jitter_timing_sampler(),
        ),
        backend,
    )


class MacOSInputControllerTests(unittest.TestCase):
    def test_hold_and_typing_delay_use_timing_sampler(self) -> None:
        backend = FakeBackend()
        timing_sampler = TimingSampler(
            TimingConfig(
                enabled=True,
                distribution="log_normal",
                delay=TimingChannelConfig(sigma=0.0, min_factor=1.0, max_factor=1.0),
                hold=TimingChannelConfig(sigma=0.0, min_factor=1.0, max_factor=1.0, min_seconds=0.04),
                typing=TimingChannelConfig(sigma=0.0, min_factor=1.0, max_factor=1.0, min_seconds=0.03),
            )
        )
        controller = MacOSInputController(
            poster=backend.post,
            pid_poster=backend.post_to_pid,
            pid_finder=lambda _process_name: None,
            sleeper=backend.sleep,
            timing_sampler=timing_sampler,
        )

        controller.tap_key("a", hold_s=0.01)
        controller.type_text("a", char_delay_s=0.01)

        self.assertIn(("sleep", 0.04), backend.events)
        self.assertIn(("sleep", 0.03), backend.events)

    def test_find_pid_in_ps_output_prefers_exact_command_name(self) -> None:
        pid = _find_pid_in_ps_output(
            "EliteDangerous64.exe",
            comm_output=" 111 /tmp/EliteDangerous64.exe\n 222 wine64-preloader\n",
            command_output=" 222 wine64-preloader C:\\\\Games\\\\EliteDangerous64.exe\n",
        )

        self.assertEqual(pid, 111)

    def test_find_pid_in_ps_output_falls_back_to_full_command_line(self) -> None:
        pid = _find_pid_in_ps_output(
            "EliteDangerous64.exe",
            comm_output=" 222 wine64-preloader\n 333 CrossOver\n",
            command_output=(
                " 222 /Applications/CrossOver.app/Contents/SharedSupport/CrossOver/bin/wine64-preloader "
                "C:\\\\Program Files (x86)\\\\Steam\\\\steamapps\\\\common\\\\Elite Dangerous\\\\EliteDangerous64.exe\n"
            ),
        )

        self.assertEqual(pid, 222)

    def test_find_pid_in_ps_output_returns_none_when_no_match_exists(self) -> None:
        pid = _find_pid_in_ps_output(
            "EliteDangerous64.exe",
            comm_output=" 222 wine64-preloader\n",
            command_output=" 222 wine64-preloader C:\\\\Program Files\\\\OtherGame.exe\n",
        )

        self.assertIsNone(pid)

    def test_tap_letter_with_hold(self) -> None:
        controller, backend = _build()

        controller.tap_key("a", hold_s=0.1)

        self.assertEqual(
            backend.events,
            [
                ("down", KEY_CODES["a"], 0, "a"),
                ("sleep", 0.1),
                ("up", KEY_CODES["a"], 0, "a"),
            ],
        )

    def test_tap_with_zero_hold_skips_sleep(self) -> None:
        controller, backend = _build()

        controller.tap_key("x")

        self.assertEqual(
            backend.events,
            [
                ("down", KEY_CODES["x"], 0, "x"),
                ("up", KEY_CODES["x"], 0, "x"),
            ],
        )

    def test_tap_with_control_modifier(self) -> None:
        controller, backend = _build()

        controller.tap_key("x", modifier="control", hold_s=0.05)

        flags = MODIFIER_FLAGS["control"]
        self.assertNotEqual(flags, 0)
        ctrl_code = KEY_CODES["left_control"]
        self.assertEqual(
            backend.events,
            [
                ("down", ctrl_code, flags, None),
                ("down", KEY_CODES["x"], flags, "x"),
                ("sleep", 0.05),
                ("up", KEY_CODES["x"], flags, "x"),
                ("up", ctrl_code, 0, None),
            ],
        )

    def test_punctuation_uses_correct_keycodes(self) -> None:
        controller, backend = _build()

        for character in (",", ".", "[", "]"):
            backend.events.clear()
            controller.tap_key(character, hold_s=0.2)

            self.assertEqual(
                backend.events,
                [
                    ("down", KEY_CODES[character], 0, character),
                    ("sleep", 0.2),
                    ("up", KEY_CODES[character], 0, character),
                ],
                msg=f"unexpected events for {character!r}",
            )

    def test_press_and_release_are_split(self) -> None:
        controller, backend = _build()

        controller.press_key("left", modifier="right_control")
        controller.release_key("left", modifier="right_control")

        flags = MODIFIER_FLAGS["right_control"]
        self.assertEqual(
            backend.events,
            [
                ("down", KEY_CODES["left"], flags, None),
                ("up", KEY_CODES["left"], flags, None),
            ],
        )

    def test_multi_char_key_sends_no_unicode_payload(self) -> None:
        controller, backend = _build()

        controller.tap_key("left_shift")

        self.assertEqual(
            backend.events,
            [
                ("down", KEY_CODES["left_shift"], 0, None),
                ("up", KEY_CODES["left_shift"], 0, None),
            ],
        )

    def test_unsupported_key_raises(self) -> None:
        controller, _ = _build()

        with self.assertRaises(ValueError):
            controller.tap_key("not_a_real_key")

    def test_unsupported_modifier_raises(self) -> None:
        controller, _ = _build()

        with self.assertRaises(ValueError):
            controller.tap_key("a", modifier="weird")

    def test_type_text_uses_real_keycodes(self) -> None:
        controller, backend = _build()

        controller.type_text("Sol", char_delay_s=0.0)

        shift_flags = MODIFIER_FLAGS["shift"]
        shift_code = KEY_CODES["left_shift"]
        s_code = KEY_CODES["s"]
        o_code = KEY_CODES["o"]
        l_code = KEY_CODES["l"]
        self.assertEqual(
            backend.events,
            [
                # "S" — shift + s
                ("down", shift_code, shift_flags, None),
                ("down", s_code, shift_flags, "s"),
                ("up", s_code, shift_flags, "s"),
                ("up", shift_code, 0, None),
                # "o"
                ("down", o_code, 0, "o"),
                ("up", o_code, 0, "o"),
                # "l"
                ("down", l_code, 0, "l"),
                ("up", l_code, 0, "l"),
            ],
        )

    def test_type_text_space_and_digit(self) -> None:
        controller, backend = _build()

        controller.type_text("A 1", char_delay_s=0.0)

        shift_flags = MODIFIER_FLAGS["shift"]
        shift_code = KEY_CODES["left_shift"]
        self.assertEqual(
            backend.events,
            [
                # "A" — shift + a
                ("down", shift_code, shift_flags, None),
                ("down", KEY_CODES["a"], shift_flags, "a"),
                ("up", KEY_CODES["a"], shift_flags, "a"),
                ("up", shift_code, 0, None),
                # " "
                ("down", KEY_CODES["space"], 0, None),
                ("up", KEY_CODES["space"], 0, None),
                # "1"
                ("down", KEY_CODES["1"], 0, "1"),
                ("up", KEY_CODES["1"], 0, "1"),
            ],
        )

    def test_set_pid_target_routes_events_via_pid_poster(self) -> None:
        controller, backend = _build()

        state = controller.set_pid_target(4242)
        controller.tap_key("a")

        self.assertEqual(state.summary(), "pid 4242")
        self.assertEqual(
            backend.events,
            [
                ("pid", 4242, "down", KEY_CODES["a"], 0, "a"),
                ("pid", 4242, "up", KEY_CODES["a"], 0, "a"),
            ],
        )

    def test_auto_target_uses_default_process_name(self) -> None:
        controller, _ = _build()

        state = controller.auto_target()

        self.assertEqual(state.pid, 4242)
        self.assertEqual(state.process_name, "EliteDangerous64.exe")
