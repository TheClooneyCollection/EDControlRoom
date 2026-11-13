"""Pass this node's journal lines on, file by file, from where the last pass stopped.

The state file maps each journal file to the lines and bytes already passed on, so a grown file
is read from there and a new one from the start. Only lines ending in a newline count, so the
line the game is still writing is read again on the next pass.
"""
from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from edcr.journal_store import SKIPPED_EVENTS, JournalLine

JOURNAL_FILE = re.compile(r"Journal\.[0-9T.-]+\.log$")
BATCH_LINES = 500
# Keeps one batch, sent to the hub as one link item, well under the link's frame limit.
BATCH_BYTES = 512 * 1024


@dataclass(frozen=True)
class SyncPosition:
    line: int
    offset: int


@dataclass(frozen=True)
class JournalBatch:
    file: str
    # Lines after the filter; their numbers keep counting the lines left out.
    lines: tuple[JournalLine, ...]
    # Where the file stands once this batch is passed on.
    position: SyncPosition


def load_positions(path: Path) -> dict[str, SyncPosition]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(raw, dict):
        return {}
    positions = {}
    for name, value in raw.items():
        if isinstance(value, dict) and isinstance(value.get("line"), int) and isinstance(value.get("offset"), int):
            positions[name] = SyncPosition(value["line"], value["offset"])
    return positions


def save_positions(path: Path, positions: dict[str, SyncPosition]) -> None:
    body = {name: {"line": p.line, "offset": p.offset} for name, p in sorted(positions.items())}
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(body, indent=1), encoding="utf-8")
    temp.replace(path)


def _is_skipped(text: str) -> bool:
    # A cheap look before parsing: only lines naming a skipped event can be one.
    if not any(f'"{name}"' in text for name in SKIPPED_EVENTS):
        return False
    try:
        return json.loads(text).get("event") in SKIPPED_EVENTS
    except (ValueError, AttributeError):
        return False


def read_batches(
    journal_dir: Path, positions: dict[str, SyncPosition], *, batch_lines: int = BATCH_LINES,
    batch_bytes: int = BATCH_BYTES,
):
    """Yield new lines per file, oldest file first, in batches of up to `batch_lines` kept lines or `batch_bytes`."""
    try:
        files = sorted(path for path in journal_dir.iterdir() if JOURNAL_FILE.fullmatch(path.name))
    except OSError:
        return
    for path in files:
        start = positions.get(path.name, SyncPosition(0, 0))
        try:
            if path.stat().st_size <= start.offset:
                continue
            with path.open("rb") as handle:
                handle.seek(start.offset)
                data = handle.read()
        except OSError:
            continue
        line, offset = start.line, start.offset
        kept: list[JournalLine] = []
        kept_bytes = 0
        for raw in data.splitlines(keepends=True):
            if not raw.endswith(b"\n"):
                break
            line += 1
            offset += len(raw)
            text = raw.decode("utf-8", errors="replace").strip()
            if text and not _is_skipped(text):
                kept.append(JournalLine(line, text))
                kept_bytes += len(raw)
            if len(kept) >= batch_lines or kept_bytes >= batch_bytes:
                yield JournalBatch(path.name, tuple(kept), SyncPosition(line, offset))
                start, kept, kept_bytes = SyncPosition(line, offset), [], 0
        # Lines left out still move the position on.
        if (line, offset) != (start.line, start.offset):
            yield JournalBatch(path.name, tuple(kept), SyncPosition(line, offset))


def batch_body(batch: JournalBatch) -> dict[str, Any]:
    """A batch as a link item body."""
    return {"file": batch.file, "lines": [[item.line, item.text] for item in batch.lines]}


def lines_from_body(body: Any) -> tuple[str, list[JournalLine]] | None:
    """The file and lines of a link item body, or None when it is not one."""
    if not isinstance(body, dict) or not isinstance(body.get("file"), str) or not JOURNAL_FILE.fullmatch(body["file"]):
        return None
    raw = body.get("lines")
    if not isinstance(raw, list):
        return None
    lines = []
    for item in raw:
        if not (isinstance(item, list) and len(item) == 2 and isinstance(item[0], int) and isinstance(item[1], str)):
            return None
        lines.append(JournalLine(item[0], item[1]))
    return body["file"], lines


def sync_journal(journal_dir: Path, state_file: Path, deliver: Callable[[JournalBatch], None]) -> int:
    """Pass every new line on; returns how many lines were passed on. The state advances per batch."""
    positions = load_positions(state_file)
    passed = 0
    for batch in read_batches(journal_dir, positions):
        if batch.lines:
            deliver(batch)
        positions[batch.file] = batch.position
        save_positions(state_file, positions)
        passed += len(batch.lines)
    return passed


def sync_journal_every(
    journal_dir: Path,
    state_file: Path,
    deliver: Callable[[JournalBatch], None],
    interval_s: float,
    *,
    stop: threading.Event,
    log: Callable[[str], None],
) -> threading.Thread:
    """Run `sync_journal` now and every `interval_s` until `stop` is set."""

    def run() -> None:
        while True:
            try:
                passed = sync_journal(journal_dir, state_file, deliver)
                if passed > 100:
                    log(f"Journal sync: {passed} lines passed on")
            except Exception as exc:  # A bad pass must not end the sync.
                log(f"Journal sync error: {exc}")
            if stop.wait(interval_s):
                return

    thread = threading.Thread(target=run, name="journal-sync", daemon=True)
    thread.start()
    return thread
