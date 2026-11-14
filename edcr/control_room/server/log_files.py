"""Log files for the headless server, so past errors outlive the terminal's scrollback.

Split like a web server's error and access logs: the server log holds EDCR's own lines and
uvicorn's errors, the access log holds one line per HTTP request (noisy with page polling).
Both rotate so they stay bounded; stderr output is unchanged.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
MAX_BYTES = 5 * 1024 * 1024
BACKUP_COUNT = 3


def rotating_file_handler(path: Path, *, max_bytes: int = MAX_BYTES, backup_count: int = BACKUP_COUNT) -> logging.Handler:
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    return handler


def log_server_to_file(path: Path | None) -> logging.Handler | None:
    """Sends the root logger (every `edcr.*` logger) to `path` too; None writes no file."""
    if path is None:
        return None
    handler = rotating_file_handler(path)
    logging.getLogger().addHandler(handler)
    return handler


def log_uvicorn_to_files(server_handler: logging.Handler | None, access_path: Path | None) -> None:
    """Call after the last `uvicorn.Config` is built: each one reapplies uvicorn's logging config,
    which drops handlers added to its loggers earlier. Its loggers do not propagate to the root."""
    if server_handler is not None:
        logging.getLogger("uvicorn").addHandler(server_handler)
    if access_path is not None:
        logging.getLogger("uvicorn.access").addHandler(rotating_file_handler(access_path))
