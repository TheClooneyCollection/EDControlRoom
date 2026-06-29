from __future__ import annotations

from .base import InputController
from edap.timing import TimingSampler


def build_input_controller(platform_name: str, *, timing_sampler: TimingSampler) -> InputController | None:
    normalized = platform_name.lower()
    if normalized == "macos":
        from .macos import MacOSInputController

        return MacOSInputController(timing_sampler=timing_sampler)
    if normalized == "linux":
        from .linux import LinuxInputController

        return LinuxInputController(timing_sampler=timing_sampler)
    if normalized == "windows":
        from .windows import WindowsInputController

        return WindowsInputController(timing_sampler=timing_sampler)
    return None
