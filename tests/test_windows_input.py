from __future__ import annotations

import unittest

from edap.platform.input.windows import KEY_CODES, WindowsInputController


class FakeBackend:
    def __init__(self) -> None:
        self.events: list[tuple] = []

    def send(self, scan_code: int, down: bool) -> None:
        self.events.append(("down" if down else "up", scan_code))

    def send_to_hwnd(self, hwnd: int, scan_code: int, down: bool) -> None:
        self.events.append(("hwnd", hwnd, "down" if down else "up", scan_code))

    def sleep(self, duration: float) -> None:
        self.events.append(("sleep", duration))


def _build() -> tuple[WindowsInputController, FakeBackend]:
    backend = FakeBackend()
    return (
        WindowsInputController(
            sender=backend.send,
            window_sender=backend.send_to_hwnd,
            pid_finder=lambda process_name: 5150 if process_name == "EliteDangerous64.exe" else None,
            pid_window_finder=lambda pid: 0xBEEF if pid == 5150 else None,
            sleeper=backend.sleep,
        ),
        backend,
    )


class WindowsInputControllerTests(unittest.TestCase):
    def test_tap_letter_with_hold(self) -> None:
        controller, backend = _build()

        controller.tap_key("a", hold_s=0.1)

        self.assertEqual(
            backend.events,
            [
                ("down", KEY_CODES["a"]),
                ("sleep", 0.1),
                ("up", KEY_CODES["a"]),
            ],
        )

    def test_tap_with_modifier_presses_modifier_first(self) -> None:
        controller, backend = _build()

        controller.tap_key("x", modifier="control", hold_s=0.05)

        self.assertEqual(
            backend.events,
            [
                ("down", KEY_CODES["left_control"]),
                ("down", KEY_CODES["x"]),
                ("sleep", 0.05),
                ("up", KEY_CODES["x"]),
                ("up", KEY_CODES["left_control"]),
            ],
        )

    def test_press_and_release_with_modifier_are_split(self) -> None:
        controller, backend = _build()

        controller.press_key("left", modifier="right_control")
        controller.release_key("left", modifier="right_control")

        self.assertEqual(
            backend.events,
            [
                ("down", KEY_CODES["right_control"]),
                ("down", KEY_CODES["left"]),
                ("up", KEY_CODES["left"]),
                ("up", KEY_CODES["right_control"]),
            ],
        )

    def test_type_text_uses_shift_for_uppercase(self) -> None:
        controller, backend = _build()

        controller.type_text("Sol", char_delay_s=0.0)

        self.assertEqual(
            backend.events,
            [
                ("down", KEY_CODES["left_shift"]),
                ("down", KEY_CODES["s"]),
                ("up", KEY_CODES["s"]),
                ("up", KEY_CODES["left_shift"]),
                ("down", KEY_CODES["o"]),
                ("up", KEY_CODES["o"]),
                ("down", KEY_CODES["l"]),
                ("up", KEY_CODES["l"]),
            ],
        )

    def test_type_text_supports_shifted_punctuation(self) -> None:
        controller, backend = _build()

        controller.type_text("?", char_delay_s=0.0)

        self.assertEqual(
            backend.events,
            [
                ("down", KEY_CODES["left_shift"]),
                ("down", KEY_CODES["/"]),
                ("up", KEY_CODES["/"]),
                ("up", KEY_CODES["left_shift"]),
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

    def test_unsupported_character_raises(self) -> None:
        controller, _ = _build()

        with self.assertRaises(ValueError):
            controller.type_text("\u00e9", char_delay_s=0.0)

    def test_set_hwnd_target_routes_events_via_window_sender(self) -> None:
        controller, backend = _build()

        state = controller.set_hwnd_target(0x1234)
        controller.tap_key("a")

        self.assertEqual(state.summary(), "hwnd 0x1234")
        self.assertEqual(
            backend.events,
            [
                ("hwnd", 0x1234, "down", KEY_CODES["a"]),
                ("hwnd", 0x1234, "up", KEY_CODES["a"]),
            ],
        )

    def test_set_pid_target_resolves_window_for_dispatch(self) -> None:
        controller, backend = _build()

        controller.set_pid_target(5150)
        controller.tap_key("a")

        self.assertEqual(
            backend.events,
            [
                ("hwnd", 0xBEEF, "down", KEY_CODES["a"]),
                ("hwnd", 0xBEEF, "up", KEY_CODES["a"]),
            ],
        )

    def test_auto_target_prefers_hwnd_when_requested(self) -> None:
        controller, _ = _build()

        state = controller.auto_target(prefer="hwnd")

        self.assertEqual(state.pid, 5150)
        self.assertEqual(state.hwnd, 0xBEEF)
        self.assertEqual(state.process_name, "EliteDangerous64.exe")
