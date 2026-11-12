from __future__ import annotations

from pathlib import Path

from .base import GamePaths


class LinuxGamePaths(GamePaths):
    def _steam_roots(self) -> list[Path]:
        return [
            Path("~/.local/share/Steam").expanduser(),
            Path("~/.steam/steam").expanduser(),
            Path("~/.var/app/com.valvesoftware.Steam/.local/share/Steam").expanduser(),
        ]

    def _find_first_directory_match(self, patterns: list[str]) -> tuple[Path | None, dict[str, object]]:
        searched_roots: list[str] = []
        candidates: list[Path] = []

        for root in self._steam_roots():
            searched_roots.append(str(root))
            if not root.exists():
                continue
            for pattern in patterns:
                candidates.extend(path for path in root.glob(pattern) if path.is_dir())

        candidates = sorted(set(candidates), key=lambda path: str(path))
        selected = candidates[0] if candidates else None
        reason = "found candidate directory" if selected else "no matching directories found under Steam roots"
        return selected, {
            "searched_roots": searched_roots,
            "searched_patterns": patterns,
            "candidate_count": len(candidates),
            "candidates": [str(path) for path in candidates[:10]],
            "selected_path": str(selected) if selected else None,
            "status": "ok" if selected else "not_found",
            "reason": reason,
        }

    def _find_latest_file_match(self, patterns: list[str]) -> tuple[Path | None, dict[str, object]]:
        searched_roots: list[str] = []
        candidates: list[Path] = []

        for root in self._steam_roots():
            searched_roots.append(str(root))
            if not root.exists():
                continue
            for pattern in patterns:
                candidates.extend(path for path in root.glob(pattern) if path.is_file())

        unique_candidates = sorted(set(candidates), key=lambda path: str(path))
        selected = None
        if unique_candidates:
            selected = max(unique_candidates, key=lambda path: path.stat().st_mtime)

        reason = "selected newest .binds file by mtime" if selected else "no .binds files found under Steam roots"
        return selected, {
            "searched_roots": searched_roots,
            "searched_patterns": patterns,
            "candidate_count": len(unique_candidates),
            "candidates": [str(path) for path in unique_candidates[:10]],
            "selected_path": str(selected) if selected else None,
            "status": "ok" if selected else "not_found",
            "reason": reason,
        }

    def describe_journal_discovery(self) -> dict[str, object]:
        patterns = [
            "steamapps/compatdata/359320/pfx/drive_c/users/*/Saved Games/Frontier Developments/Elite Dangerous",
        ]
        _, report = self._find_first_directory_match(patterns)
        return report

    def describe_bindings_discovery(self) -> dict[str, object]:
        patterns = [
            "steamapps/compatdata/359320/pfx/drive_c/users/*/AppData/Local/Frontier Developments/Elite Dangerous/Options/Bindings/*.binds",
            "steamapps/compatdata/359320/pfx/drive_c/users/*/Local Settings/Application Data/Frontier Developments/Elite Dangerous/Options/Bindings/*.binds",
        ]
        _, report = self._find_latest_file_match(patterns)
        return report

    def default_journal_dir(self) -> Path | None:
        selected, _ = self._find_first_directory_match(
            ["steamapps/compatdata/359320/pfx/drive_c/users/*/Saved Games/Frontier Developments/Elite Dangerous"]
        )
        return selected

    def default_bindings_file(self) -> Path | None:
        selected, _ = self._find_latest_file_match(
            [
                "steamapps/compatdata/359320/pfx/drive_c/users/*/AppData/Local/Frontier Developments/Elite Dangerous/Options/Bindings/*.binds",
                "steamapps/compatdata/359320/pfx/drive_c/users/*/Local Settings/Application Data/Frontier Developments/Elite Dangerous/Options/Bindings/*.binds",
            ]
        )
        return selected
