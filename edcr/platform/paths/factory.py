from __future__ import annotations

from .base import GamePaths


def build_game_paths(platform_name: str) -> GamePaths | None:
    normalized = platform_name.lower()
    if normalized == "linux":
        from .linux import LinuxGamePaths

        return LinuxGamePaths()
    if normalized == "macos":
        from .macos import MacOSGamePaths

        return MacOSGamePaths()
    if normalized == "windows":
        from .windows import WindowsGamePaths

        return WindowsGamePaths()
    return None
