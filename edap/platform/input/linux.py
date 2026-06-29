from __future__ import annotations

from collections.abc import Callable, Sequence
from shutil import which
from subprocess import CalledProcessError, run
from time import sleep as _default_sleep

from edap.timing import TimingSampler

from .base import InputController, InputTargetState


KEY_NAMES: dict[str, str] = {
    "escape": "Escape",
    "esc": "Escape",
    "1": "1",
    "2": "2",
    "3": "3",
    "4": "4",
    "5": "5",
    "6": "6",
    "7": "7",
    "8": "8",
    "9": "9",
    "0": "0",
    "-": "minus",
    "=": "equal",
    "backspace": "BackSpace",
    "tab": "Tab",
    "q": "q",
    "w": "w",
    "e": "e",
    "r": "r",
    "t": "t",
    "y": "y",
    "u": "u",
    "i": "i",
    "o": "o",
    "p": "p",
    "[": "bracketleft",
    "]": "bracketright",
    "enter": "Return",
    "return": "Return",
    "left_control": "Control_L",
    "right_control": "Control_R",
    "a": "a",
    "s": "s",
    "d": "d",
    "f": "f",
    "g": "g",
    "h": "h",
    "j": "j",
    "k": "k",
    "l": "l",
    ";": "semicolon",
    "'": "apostrophe",
    "`": "grave",
    "left_shift": "Shift_L",
    "\\": "backslash",
    "z": "z",
    "x": "x",
    "c": "c",
    "v": "v",
    "b": "b",
    "n": "n",
    "m": "m",
    ",": "comma",
    ".": "period",
    "/": "slash",
    "right_shift": "Shift_R",
    "left_alt": "Alt_L",
    "right_alt": "Alt_R",
    "left_option": "Alt_L",
    "right_option": "Alt_R",
    "space": "space",
    "f1": "F1",
    "f2": "F2",
    "f3": "F3",
    "f4": "F4",
    "f5": "F5",
    "f6": "F6",
    "f7": "F7",
    "f8": "F8",
    "f9": "F9",
    "f10": "F10",
    "f11": "F11",
    "f12": "F12",
    "f13": "F13",
    "f14": "F14",
    "f15": "F15",
    "home": "Home",
    "up": "Up",
    "page_up": "Page_Up",
    "left": "Left",
    "right": "Right",
    "end": "End",
    "down": "Down",
    "page_down": "Page_Down",
    "insert": "Insert",
    "delete": "Delete",
    "left_command": "Super_L",
    "right_command": "Super_R",
    "numpad_0": "KP_0",
    "numpad_1": "KP_1",
    "numpad_2": "KP_2",
    "numpad_3": "KP_3",
    "numpad_4": "KP_4",
    "numpad_5": "KP_5",
    "numpad_6": "KP_6",
    "numpad_7": "KP_7",
    "numpad_8": "KP_8",
    "numpad_9": "KP_9",
}


MODIFIER_KEY_NAMES: dict[str, str] = {
    "shift": KEY_NAMES["left_shift"],
    "left_shift": KEY_NAMES["left_shift"],
    "right_shift": KEY_NAMES["right_shift"],
    "control": KEY_NAMES["left_control"],
    "ctrl": KEY_NAMES["left_control"],
    "left_control": KEY_NAMES["left_control"],
    "right_control": KEY_NAMES["right_control"],
    "alt": KEY_NAMES["left_alt"],
    "option": KEY_NAMES["left_alt"],
    "left_alt": KEY_NAMES["left_alt"],
    "right_alt": KEY_NAMES["right_alt"],
    "left_option": KEY_NAMES["left_option"],
    "right_option": KEY_NAMES["right_option"],
    "command": KEY_NAMES["left_command"],
    "cmd": KEY_NAMES["left_command"],
    "left_command": KEY_NAMES["left_command"],
    "right_command": KEY_NAMES["right_command"],
}


RunnerFn = Callable[[Sequence[str]], None]
SleeperFn = Callable[[float], None]


def _run_xdotool(args: Sequence[str]) -> None:
    if which("xdotool") is None:
        raise RuntimeError("xdotool is required for the Linux input backend.")
    try:
        run(args, check=True, capture_output=True, text=True)
    except CalledProcessError as exc:  # pragma: no cover - requires real xdotool failure
        stderr = exc.stderr.strip() if exc.stderr else ""
        detail = f" {stderr}" if stderr else ""
        raise RuntimeError(f"xdotool command failed:{detail}") from exc


def _make_default_runner() -> RunnerFn:
    def runner(args: Sequence[str]) -> None:
        _run_xdotool(args)

    return runner


class LinuxInputController(InputController):
    def __init__(
        self,
        *,
        runner: RunnerFn | None = None,
        sleeper: SleeperFn | None = None,
        timing_sampler: TimingSampler,
    ) -> None:
        self._runner = runner if runner is not None else _make_default_runner()
        self._sleeper = sleeper if sleeper is not None else _default_sleep
        self._timing_sampler = timing_sampler
        self._target = InputTargetState(platform="linux", mode="foreground")

    def press_key(self, key: str, modifier: str | None = None) -> None:
        key_name, modifier_name = self._resolve(key, modifier)
        if modifier_name is not None:
            self._runner(["xdotool", "keydown", modifier_name])
        self._runner(["xdotool", "keydown", key_name])

    def release_key(self, key: str, modifier: str | None = None) -> None:
        key_name, modifier_name = self._resolve(key, modifier)
        self._runner(["xdotool", "keyup", key_name])
        if modifier_name is not None:
            self._runner(["xdotool", "keyup", modifier_name])

    def tap_key(self, key: str, modifier: str | None = None, hold_s: float = 0.0) -> None:
        key_name, modifier_name = self._resolve(key, modifier)
        if modifier_name is not None:
            self._runner(["xdotool", "keydown", modifier_name])
        self._runner(["xdotool", "keydown", key_name])
        if hold_s > 0:
            sampled_hold_s = self._timing_sampler.sample_hold(hold_s)
            self._sleeper(sampled_hold_s)
        self._runner(["xdotool", "keyup", key_name])
        if modifier_name is not None:
            self._runner(["xdotool", "keyup", modifier_name])

    def type_text(self, text: str, char_delay_s: float = 0.05) -> None:
        sampled_delay_s = self._timing_sampler.sample_typing_delay(char_delay_s)
        delay_ms = max(0, round(sampled_delay_s * 1000))
        self._runner(["xdotool", "type", "--delay", str(delay_ms), text])

    def current_target(self) -> InputTargetState:
        return self._target

    def set_foreground_target(self) -> InputTargetState:
        self._target = InputTargetState(platform="linux", mode="foreground")
        return self._target

    def _resolve(self, key: str, modifier: str | None) -> tuple[str, str | None]:
        normalized = key.lower()
        if normalized not in KEY_NAMES:
            raise ValueError(f"Unsupported key: {key}")

        modifier_name = None
        if modifier is not None:
            normalized_modifier = modifier.lower()
            if normalized_modifier not in MODIFIER_KEY_NAMES:
                raise ValueError(f"Unsupported modifier: {modifier}")
            modifier_name = MODIFIER_KEY_NAMES[normalized_modifier]

        return KEY_NAMES[normalized], modifier_name
