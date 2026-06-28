from __future__ import annotations

import unittest

from edap.platform.input.linux import KEY_NAMES, LinuxInputController


class FakeBackend:
    def __init__(self) -> None:
        self.commands: list[tuple[str, ...]] = []

    def run(self, args: tuple[str, ...] | list[str]) -> None:
        self.commands.append(tuple(args))

    def sleep(self, duration: float) -> None:
        self.commands.append(("sleep", str(duration)))


def _build() -> tuple[LinuxInputController, FakeBackend]:
    backend = FakeBackend()
    return (
        LinuxInputController(runner=backend.run, sleeper=backend.sleep),
        backend,
    )


class LinuxInputControllerTests(unittest.TestCase):
    def test_tap_letter_with_hold(self) -> None:
        controller, backend = _build()

        controller.tap_key("a", hold_s=0.1)

        self.assertEqual(
            backend.commands,
            [
                ("xdotool", "keydown", KEY_NAMES["a"]),
                ("sleep", "0.1"),
                ("xdotool", "keyup", KEY_NAMES["a"]),
            ],
        )

    def test_tap_with_modifier_presses_modifier_first(self) -> None:
        controller, backend = _build()

        controller.tap_key("x", modifier="control", hold_s=0.05)

        self.assertEqual(
            backend.commands,
            [
                ("xdotool", "keydown", KEY_NAMES["left_control"]),
                ("xdotool", "keydown", KEY_NAMES["x"]),
                ("sleep", "0.05"),
                ("xdotool", "keyup", KEY_NAMES["x"]),
                ("xdotool", "keyup", KEY_NAMES["left_control"]),
            ],
        )

    def test_press_and_release_with_modifier_are_split(self) -> None:
        controller, backend = _build()

        controller.press_key("left", modifier="right_control")
        controller.release_key("left", modifier="right_control")

        self.assertEqual(
            backend.commands,
            [
                ("xdotool", "keydown", KEY_NAMES["right_control"]),
                ("xdotool", "keydown", KEY_NAMES["left"]),
                ("xdotool", "keyup", KEY_NAMES["left"]),
                ("xdotool", "keyup", KEY_NAMES["right_control"]),
            ],
        )

    def test_type_text_uses_xdotool_type(self) -> None:
        controller, backend = _build()

        controller.type_text("Sol", char_delay_s=0.012)

        self.assertEqual(
            backend.commands,
            [
                ("xdotool", "type", "--delay", "12", "Sol"),
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

    def test_current_target_defaults_to_foreground(self) -> None:
        controller, _ = _build()

        self.assertEqual(controller.current_target().summary(), "foreground window")

    def test_pid_targeting_is_not_supported(self) -> None:
        controller, _ = _build()

        with self.assertRaisesRegex(RuntimeError, "pid-targeted"):
            controller.set_pid_target(1234)
