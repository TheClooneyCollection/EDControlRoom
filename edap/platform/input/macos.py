from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from subprocess import run
from time import sleep as _default_sleep

try:
    from Quartz import (
        CGEventCreateKeyboardEvent,
        CGEventKeyboardSetUnicodeString,
        CGEventPost,
        CGEventPostToPid,
        CGEventSetFlags,
        CGEventSourceCreate,
        kCGEventFlagMaskAlternate,
        kCGEventFlagMaskCommand,
        kCGEventFlagMaskControl,
        kCGEventFlagMaskShift,
        kCGEventSourceStateHIDSystemState,
        kCGHIDEventTap,
    )
except ImportError:  # pragma: no cover - exercised implicitly on non-macOS CI runners
    CGEventCreateKeyboardEvent = None
    CGEventKeyboardSetUnicodeString = None
    CGEventPost = None
    CGEventPostToPid = None
    CGEventSetFlags = None
    CGEventSourceCreate = None
    kCGEventFlagMaskAlternate = 1 << 19
    kCGEventFlagMaskCommand = 1 << 20
    kCGEventFlagMaskControl = 1 << 18
    kCGEventFlagMaskShift = 1 << 17
    kCGEventSourceStateHIDSystemState = None
    kCGHIDEventTap = None

from .base import (
    DEFAULT_AUTO_TARGET_PROCESS_NAME,
    InputController,
    InputTargetState,
)


KEY_CODES: dict[str, int] = {
    "a": 0, "s": 1, "d": 2, "f": 3, "h": 4, "g": 5, "z": 6, "x": 7, "c": 8, "v": 9,
    "b": 11, "q": 12, "w": 13, "e": 14, "r": 15, "y": 16, "t": 17,
    "1": 18, "2": 19, "3": 20, "4": 21, "6": 22, "5": 23,
    "=": 24, "9": 25, "7": 26, "-": 27, "8": 28, "0": 29,
    "]": 30, "o": 31, "u": 32, "[": 33, "i": 34, "p": 35,
    "l": 37, "j": 38, "'": 39, "k": 40, ";": 41, "\\": 42,
    ",": 43, "/": 44, "n": 45, "m": 46, ".": 47,
    "enter": 36,
    "return": 36,
    "tab": 48,
    "space": 49,
    "`": 50,
    "backspace": 51,
    "escape": 53,
    "esc": 53,
    "right_command": 54,
    "left_command": 55,
    "left_shift": 56,
    "right_shift": 60,
    "left_option": 58,
    "right_option": 61,
    "left_alt": 58,
    "right_alt": 61,
    "left_control": 59,
    "right_control": 62,
    "numpad_0": 82, "numpad_1": 83, "numpad_2": 84, "numpad_3": 85,
    "numpad_4": 86, "numpad_5": 87, "numpad_6": 88, "numpad_7": 89,
    "numpad_8": 91, "numpad_9": 92,
    "home": 115,
    "page_up": 116,
    "delete": 117,
    "end": 119,
    "page_down": 121,
    "left": 123,
    "right": 124,
    "down": 125,
    "up": 126,
    "f1": 122, "f2": 120, "f3": 99, "f4": 118, "f5": 96, "f6": 97,
    "f7": 98, "f8": 100, "f9": 101, "f10": 109, "f11": 103, "f12": 111,
    "f13": 105, "f14": 107, "f15": 113, "f16": 106, "f17": 64,
    "f18": 79, "f19": 80, "f20": 90,
}


MODIFIER_FLAGS: dict[str, int] = {
    "shift": kCGEventFlagMaskShift,
    "left_shift": kCGEventFlagMaskShift,
    "right_shift": kCGEventFlagMaskShift,
    "control": kCGEventFlagMaskControl,
    "ctrl": kCGEventFlagMaskControl,
    "left_control": kCGEventFlagMaskControl,
    "right_control": kCGEventFlagMaskControl,
    "option": kCGEventFlagMaskAlternate,
    "alt": kCGEventFlagMaskAlternate,
    "left_option": kCGEventFlagMaskAlternate,
    "right_option": kCGEventFlagMaskAlternate,
    "left_alt": kCGEventFlagMaskAlternate,
    "right_alt": kCGEventFlagMaskAlternate,
    "command": kCGEventFlagMaskCommand,
    "cmd": kCGEventFlagMaskCommand,
    "left_command": kCGEventFlagMaskCommand,
    "right_command": kCGEventFlagMaskCommand,
}

# Maps modifier names to the physical key code to press/release.
# Generic names (shift, ctrl, etc.) map to the left-hand variant.
MODIFIER_KEYCODES: dict[str, int] = {
    "shift": KEY_CODES["left_shift"],
    "left_shift": KEY_CODES["left_shift"],
    "right_shift": KEY_CODES["right_shift"],
    "control": KEY_CODES["left_control"],
    "ctrl": KEY_CODES["left_control"],
    "left_control": KEY_CODES["left_control"],
    "right_control": KEY_CODES["right_control"],
    "option": KEY_CODES["left_option"],
    "alt": KEY_CODES["left_option"],
    "left_option": KEY_CODES["left_option"],
    "right_option": KEY_CODES["right_option"],
    "left_alt": KEY_CODES["left_option"],
    "right_alt": KEY_CODES["right_option"],
    "command": KEY_CODES["left_command"],
    "cmd": KEY_CODES["left_command"],
    "left_command": KEY_CODES["left_command"],
    "right_command": KEY_CODES["right_command"],
}


PosterFn = Callable[[int, bool, int, "str | None"], None]
PidPosterFn = Callable[[int, int, bool, int, "str | None"], None]
SleeperFn = Callable[[float], None]
PidFinderFn = Callable[[str], int | None]


def _make_default_poster() -> PosterFn:
    if CGEventSourceCreate is None or CGEventCreateKeyboardEvent is None or CGEventPost is None:
        raise RuntimeError("Quartz is required for the default macOS input backend.")
    source = CGEventSourceCreate(kCGEventSourceStateHIDSystemState)

    def poster(keycode: int, down: bool, flags: int, unicode_char: str | None) -> None:
        event = CGEventCreateKeyboardEvent(source, keycode, down)
        if flags and CGEventSetFlags is not None:
            CGEventSetFlags(event, flags)
        if unicode_char is not None and CGEventKeyboardSetUnicodeString is not None:
            CGEventKeyboardSetUnicodeString(event, 1, unicode_char)
        CGEventPost(kCGHIDEventTap, event)

    return poster


def _make_default_pid_poster() -> PidPosterFn:
    if CGEventSourceCreate is None or CGEventCreateKeyboardEvent is None or CGEventPostToPid is None:
        raise RuntimeError("Quartz pid-targeted posting is unavailable on this macOS runtime.")
    source = CGEventSourceCreate(kCGEventSourceStateHIDSystemState)

    def poster(pid: int, keycode: int, down: bool, flags: int, unicode_char: str | None) -> None:
        event = CGEventCreateKeyboardEvent(source, keycode, down)
        if flags and CGEventSetFlags is not None:
            CGEventSetFlags(event, flags)
        if unicode_char is not None and CGEventKeyboardSetUnicodeString is not None:
            CGEventKeyboardSetUnicodeString(event, 1, unicode_char)
        CGEventPostToPid(pid, event)

    return poster


def _find_pid_in_ps_output(
    process_name: str,
    *,
    comm_output: str,
    command_output: str,
) -> int | None:
    wanted = Path(process_name.strip()).name.lower()
    if not wanted:
        return None

    for line in comm_output.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) != 2:
            continue
        pid_raw, command = parts
        if Path(command).name.lower() != wanted:
            continue
        try:
            return int(pid_raw)
        except ValueError:
            continue

    for line in command_output.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) != 2:
            continue
        pid_raw, command = parts
        if wanted not in command.lower():
            continue
        try:
            return int(pid_raw)
        except ValueError:
            continue

    return None


def _find_pid_by_process_name(process_name: str) -> int | None:
    comm_result = run(
        ["ps", "-axo", "pid=,comm="],
        check=False,
        capture_output=True,
        text=True,
    )
    if comm_result.returncode != 0:
        return None
    command_result = run(
        ["ps", "-axo", "pid=,command="],
        check=False,
        capture_output=True,
        text=True,
    )
    command_output = command_result.stdout if command_result.returncode == 0 else ""
    return _find_pid_in_ps_output(
        process_name,
        comm_output=comm_result.stdout,
        command_output=command_output,
    )


class MacOSInputController(InputController):
    def __init__(
        self,
        *,
        poster: PosterFn | None = None,
        pid_poster: PidPosterFn | None = None,
        pid_finder: PidFinderFn | None = None,
        sleeper: SleeperFn | None = None,
    ) -> None:
        self._poster = poster if poster is not None else _make_default_poster()
        self._pid_poster = pid_poster
        self._pid_finder = pid_finder if pid_finder is not None else _find_pid_by_process_name
        self._sleeper = sleeper if sleeper is not None else _default_sleep
        self._target = InputTargetState(platform="macos", mode="foreground")

    def press_key(self, key: str, modifier: str | None = None) -> None:
        keycode, flags, unicode_char = self._resolve(key, modifier)
        self._dispatch_event(keycode, True, flags, unicode_char)

    def release_key(self, key: str, modifier: str | None = None) -> None:
        keycode, flags, unicode_char = self._resolve(key, modifier)
        self._dispatch_event(keycode, False, flags, unicode_char)

    def tap_key(self, key: str, modifier: str | None = None, hold_s: float = 0.0) -> None:
        keycode, flags, unicode_char = self._resolve(key, modifier)
        mod_keycode = MODIFIER_KEYCODES.get(modifier.lower()) if modifier else None
        if mod_keycode is not None:
            self._dispatch_event(mod_keycode, True, flags, None)
        self._dispatch_event(keycode, True, flags, unicode_char)
        if hold_s > 0:
            self._sleeper(hold_s)
        self._dispatch_event(keycode, False, flags, unicode_char)
        if mod_keycode is not None:
            self._dispatch_event(mod_keycode, False, 0, None)

    def type_text(self, text: str, char_delay_s: float = 0.05) -> None:
        _SPECIAL: dict[str, str] = {"\n": "enter", "\r": "return", "\t": "tab", "\x1b": "esc"}
        # Characters that are the shifted variant of a base key.
        _SHIFTED: dict[str, str] = {
            "!": "1", "@": "2", "#": "3", "$": "4", "%": "5",
            "^": "6", "&": "7", "*": "8", "(": "9", ")": "0",
            "_": "-", "+": "=", "{": "[", "}": "]", "|": "\\",
            ":": ";", '"': "'", "<": ",", ">": ".", "?": "/", "~": "`",
        }
        for char in text:
            if char in _SPECIAL:
                self.tap_key(_SPECIAL[char])
            elif char == " ":
                self.tap_key("space")
            elif char.lower() in KEY_CODES:
                self.tap_key(char.lower(), modifier="left_shift" if char.isupper() else None)
            elif char in _SHIFTED:
                self.tap_key(_SHIFTED[char], modifier="left_shift")
            else:
                raise ValueError(f"Unsupported character for macOS input: {char!r}")
            if char_delay_s > 0:
                self._sleeper(char_delay_s)

    def current_target(self) -> InputTargetState:
        return self._target

    def set_foreground_target(self) -> InputTargetState:
        self._target = InputTargetState(platform="macos", mode="foreground")
        return self._target

    def set_pid_target(self, pid: int) -> InputTargetState:
        if pid <= 0:
            raise ValueError("pid must be a positive integer")
        self._target = InputTargetState(platform="macos", mode="pid", pid=pid)
        return self._target

    def auto_target(
        self,
        process_name: str = DEFAULT_AUTO_TARGET_PROCESS_NAME,
        *,
        prefer: str = "pid",
    ) -> InputTargetState:
        if prefer != "pid":
            raise RuntimeError("macOS targeted input supports pid targeting, not hwnd targeting.")
        pid = self._pid_finder(process_name)
        if pid is None:
            raise RuntimeError(f"No process matched {process_name!r}.")
        self._target = InputTargetState(
            platform="macos",
            mode="pid",
            pid=pid,
            process_name=process_name,
        )
        return self._target

    def _dispatch_event(self, keycode: int, down: bool, flags: int, unicode_char: str | None) -> None:
        target = self._target
        if target.mode == "pid":
            if target.pid is None:
                raise RuntimeError("Targeted macOS input requires a pid.")
            pid_poster = self._pid_poster
            if pid_poster is None:
                pid_poster = _make_default_pid_poster()
                self._pid_poster = pid_poster
            pid_poster(target.pid, keycode, down, flags, unicode_char)
            return
        self._poster(keycode, down, flags, unicode_char)

    def _resolve(self, key: str, modifier: str | None) -> tuple[int, int, str | None]:
        normalized = key.lower()
        if normalized not in KEY_CODES:
            raise ValueError(f"Unsupported key: {key}")
        keycode = KEY_CODES[normalized]

        flags = 0
        if modifier is not None:
            normalized_mod = modifier.lower()
            if normalized_mod not in MODIFIER_FLAGS:
                raise ValueError(f"Unsupported modifier: {modifier}")
            flags = MODIFIER_FLAGS[normalized_mod]

        unicode_char = key if len(key) == 1 else None
        return keycode, flags, unicode_char
