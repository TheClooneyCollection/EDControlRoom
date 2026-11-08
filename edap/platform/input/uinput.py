from __future__ import annotations

import os
import struct
from collections.abc import Callable
from time import sleep as _default_sleep

from edap.timing import TimingSampler

from .base import InputController, InputTargetState
from .scancodes import KEY_CODES, resolve_scancode


# Linux evdev codes equal set-1 scan codes except for extended keys and F13-F15.
_EVDEV_EXTENDED: dict[int, int] = {
    0x1C: 96,   # numpad_enter
    0x1D: 97,   # right_control
    0x35: 98,   # numpad_divide
    0x38: 100,  # right_alt
    0x47: 102,  # home
    0x48: 103,  # up
    0x49: 104,  # page_up
    0x4B: 105,  # left
    0x4D: 106,  # right
    0x4F: 107,  # end
    0x50: 108,  # down
    0x51: 109,  # page_down
    0x52: 110,  # insert
    0x53: 111,  # delete
    0x5B: 125,  # left_command (left meta)
    0x5C: 126,  # right_command (right meta)
}
_EVDEV_NON_EXTENDED: dict[int, int] = {0x64: 183, 0x65: 184, 0x66: 185}  # f13-f15

_TYPE_SPECIAL: dict[str, str] = {"\n": "enter", "\r": "return", "\t": "tab", "\x1b": "esc", " ": "space"}
# Characters that are the shifted variant of a base key on a US layout.
_TYPE_SHIFTED: dict[str, str] = {
    "!": "1", "@": "2", "#": "3", "$": "4", "%": "5",
    "^": "6", "&": "7", "*": "8", "(": "9", ")": "0",
    "_": "-", "+": "=", "{": "[", "}": "]", "|": "\\",
    ":": ";", '"': "'", "<": ",", ">": ".", "?": "/", "~": "`",
}


def evdev_code(key: str, *, modifier: bool = False) -> int:
    code, extended = resolve_scancode(key, modifier=modifier)
    if extended:
        return _EVDEV_EXTENDED[code]
    return _EVDEV_NON_EXTENDED.get(code, code)


WriteKeyFn = Callable[[int, bool], None]
SleeperFn = Callable[[float], None]
CloseFn = Callable[[], None]


class LinuxUinputController(InputController):
    """Drives the game through a kernel virtual keyboard, so it works under X11 and gamescope alike."""

    def __init__(
        self,
        *,
        write_key: WriteKeyFn,
        close_device: CloseFn,
        sleeper: SleeperFn,
        timing_sampler: TimingSampler,
    ) -> None:
        self._write_key = write_key
        self._close_device = close_device
        self._sleeper = sleeper
        self._timing_sampler = timing_sampler
        self._target = InputTargetState(platform="linux", mode="foreground")

    def press_key(self, key: str, modifier: str | None = None) -> None:
        code, modifier_code = self._resolve(key, modifier)
        if modifier_code is not None:
            self._write_key(modifier_code, True)
        self._write_key(code, True)

    def release_key(self, key: str, modifier: str | None = None) -> None:
        code, modifier_code = self._resolve(key, modifier)
        self._write_key(code, False)
        if modifier_code is not None:
            self._write_key(modifier_code, False)

    def tap_key(self, key: str, modifier: str | None = None, hold_s: float = 0.0) -> None:
        self.press_key(key, modifier)
        if hold_s > 0:
            self._sleeper(self._timing_sampler.sample_hold(hold_s))
        self.release_key(key, modifier)

    def type_text(self, text: str, char_delay_s: float = 0.05) -> None:
        for char in text:
            if char in _TYPE_SPECIAL:
                self.tap_key(_TYPE_SPECIAL[char])
            elif char.lower() in KEY_CODES:
                self.tap_key(char.lower(), modifier="left_shift" if char.isupper() else None)
            elif char in _TYPE_SHIFTED:
                self.tap_key(_TYPE_SHIFTED[char], modifier="left_shift")
            else:
                raise ValueError(f"Unsupported character for Linux uinput input: {char!r}")
            if char_delay_s > 0:
                self._sleeper(self._timing_sampler.sample_typing_delay(char_delay_s))

    def current_target(self) -> InputTargetState:
        return self._target

    def set_foreground_target(self) -> InputTargetState:
        self._target = InputTargetState(platform="linux", mode="foreground")
        return self._target

    def input_status(self) -> dict[str, object]:
        return {"target": self._target.summary(), "backend": "uinput"}

    def close(self) -> None:
        self._close_device()

    def _resolve(self, key: str, modifier: str | None) -> tuple[int, int | None]:
        code = evdev_code(key)
        return code, evdev_code(modifier, modifier=True) if modifier is not None else None


_UINPUT_PATH = "/dev/uinput"
_UI_SET_EVBIT = 0x40045564
_UI_SET_KEYBIT = 0x40045565
_UI_DEV_SETUP = 0x405C5503
_UI_DEV_CREATE = 0x5501
_UI_DEV_DESTROY = 0x5502
_EV_SYN = 0
_EV_KEY = 1
_BUS_USB = 0x03
_DEVICE_NAME = b"EDControlRoom virtual keyboard"
# libinput and the compositor need a moment to adopt a new device; earlier events are dropped.
_DEVICE_SETTLE_S = 1.0


class UinputKeyboard:
    """Thin /dev/uinput adapter: the device is created on first key so diagnostics never create one."""

    def __init__(self) -> None:
        self._fd: int | None = None

    def write_key(self, code: int, down: bool) -> None:
        fd = self._open()
        os.write(fd, struct.pack("llHHi", 0, 0, _EV_KEY, code, 1 if down else 0))
        os.write(fd, struct.pack("llHHi", 0, 0, _EV_SYN, 0, 0))

    def close(self) -> None:
        if self._fd is None:
            return
        import fcntl

        fd, self._fd = self._fd, None
        try:
            fcntl.ioctl(fd, _UI_DEV_DESTROY)
        finally:
            os.close(fd)

    def _open(self) -> int:
        if self._fd is not None:
            return self._fd
        import fcntl  # POSIX-only; kept local so the module imports on every platform

        try:
            fd = os.open(_UINPUT_PATH, os.O_WRONLY | os.O_NONBLOCK)
        except OSError as exc:
            raise RuntimeError(
                f"Cannot open {_UINPUT_PATH} ({exc.strerror}); the user needs write access to it for uinput input."
            ) from exc
        fcntl.ioctl(fd, _UI_SET_EVBIT, _EV_KEY)
        for code in range(1, 249):
            fcntl.ioctl(fd, _UI_SET_KEYBIT, code)
        fcntl.ioctl(fd, _UI_DEV_SETUP, struct.pack("HHHH80sI", _BUS_USB, 0x1234, 0x5678, 1, _DEVICE_NAME, 0))
        fcntl.ioctl(fd, _UI_DEV_CREATE)
        self._fd = fd
        _default_sleep(_DEVICE_SETTLE_S)
        return fd


def build_uinput_controller(*, timing_sampler: TimingSampler) -> LinuxUinputController:
    keyboard = UinputKeyboard()
    return LinuxUinputController(
        write_key=keyboard.write_key,
        close_device=keyboard.close,
        sleeper=_default_sleep,
        timing_sampler=timing_sampler,
    )
