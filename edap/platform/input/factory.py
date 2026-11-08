from __future__ import annotations

from .base import InputController
from edap.timing import TimingSampler
from edap.config import InputConfig


def build_input_controller(platform_name: str, *, input_config: InputConfig, timing_sampler: TimingSampler) -> InputController | None:
    normalized = platform_name.lower()
    if input_config.target == "wine_helper" and normalized != "macos":
        raise RuntimeError("wine_helper input is only supported on macOS.")
    if normalized == "macos":
        from .macos import MacOSInputController

        from .wine_helper import build_wine_helper

        controller = MacOSInputController(timing_sampler=timing_sampler, wine_helper=build_wine_helper(input_config.wine_helper))
        if input_config.target == "wine_helper":
            # Diagnostics and remote clients build controllers too; only the local host starts the helper.
            controller.select_wine_helper_mode()
        elif input_config.target == "pid":
            controller.auto_target()
        return controller
    if normalized == "linux":
        if input_config.linux_backend == "uinput":
            from .uinput import build_uinput_controller

            controller = build_uinput_controller(timing_sampler=timing_sampler)
        else:
            from .linux import LinuxInputController

            controller = LinuxInputController(timing_sampler=timing_sampler)
        if input_config.target == "pid":
            controller.auto_target()
        return controller
    if normalized == "windows":
        from .windows import WindowsInputController

        controller = WindowsInputController(timing_sampler=timing_sampler)
        if input_config.target == "pid":
            controller.auto_target()
        return controller
    return None
