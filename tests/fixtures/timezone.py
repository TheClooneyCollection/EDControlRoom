"""Deterministic timezone wiring for tests unrelated to the OS timezone adapter."""
from datetime import timezone
from unittest import addModuleCleanup
from unittest.mock import patch


def use_utc_timezone(module: str) -> None:
    # These flows exercise window calculations, not the host timezone database.
    # OS/DST conversion is covered separately in test_haul_history.
    adapter = patch(f"{module}.SystemLocalTimezone", new=lambda: timezone.utc)
    adapter.start()
    addModuleCleanup(adapter.stop)
