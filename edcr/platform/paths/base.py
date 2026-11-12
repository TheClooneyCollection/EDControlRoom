from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class GamePaths(ABC):
    @abstractmethod
    def default_journal_dir(self) -> Path | None:
        """Return the default journal directory for the platform."""

    @abstractmethod
    def default_bindings_file(self) -> Path | None:
        """Return the default bindings file for the platform."""
