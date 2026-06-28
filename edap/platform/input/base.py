from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


DEFAULT_AUTO_TARGET_PROCESS_NAME = "EliteDangerous64.exe"


@dataclass(frozen=True)
class InputTargetState:
    platform: str
    mode: str
    pid: int | None = None
    hwnd: int | None = None
    process_name: str | None = None

    def summary(self) -> str:
        if self.mode == "pid" and self.pid is not None:
            label = f"pid {self.pid}"
            if self.process_name:
                return f"{label} ({self.process_name})"
            return label
        if self.mode == "hwnd" and self.hwnd is not None:
            label = f"hwnd 0x{self.hwnd:X}"
            if self.process_name:
                return f"{label} ({self.process_name})"
            return label
        return "foreground window"


class InputController(ABC):
    @abstractmethod
    def press_key(self, key: str, modifier: str | None = None) -> None:
        """Press a key, optionally with a modifier."""

    @abstractmethod
    def release_key(self, key: str, modifier: str | None = None) -> None:
        """Release a key, optionally with a modifier."""

    @abstractmethod
    def tap_key(self, key: str, modifier: str | None = None, hold_s: float = 0.0) -> None:
        """Press and release a key sequence."""

    @abstractmethod
    def type_text(self, text: str, char_delay_s: float = 0.05) -> None:
        """Type a string of text, one character at a time."""

    def current_target(self) -> InputTargetState:
        return InputTargetState(platform="unknown", mode="foreground")

    def set_foreground_target(self) -> InputTargetState:
        raise RuntimeError("This input backend does not expose target selection.")

    def set_pid_target(self, pid: int) -> InputTargetState:
        raise RuntimeError("This input backend does not support pid-targeted input.")

    def set_hwnd_target(self, hwnd: int) -> InputTargetState:
        raise RuntimeError("This input backend does not support hwnd-targeted input.")

    def auto_target(
        self,
        process_name: str = DEFAULT_AUTO_TARGET_PROCESS_NAME,
        *,
        prefer: str = "pid",
    ) -> InputTargetState:
        raise RuntimeError("This input backend does not support automatic target detection.")
