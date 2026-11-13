from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from edcr.journal_store import JournalStore
from edcr.journal_sync import SyncPosition, load_positions, read_batches, sync_journal

FIRST = "Journal.2026-11-10T080000.01.log"
SECOND = "Journal.2026-11-11T080000.01.log"


def line(event: str, second: int, **fields) -> str:
    return json.dumps({"timestamp": f"2026-11-10T08:00:{second:02d}Z", "event": event, **fields}) + "\n"


class JournalSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.dir = Path(temp.name) / "journals"
        self.dir.mkdir()
        self.state = Path(temp.name) / "sync.json"
        self.store = JournalStore(sqlite3.connect(":memory:"))

    def write(self, name: str, text: str) -> None:
        with (self.dir / name).open("a", encoding="utf-8") as handle:
            handle.write(text)

    def sync(self) -> int:
        return sync_journal(self.dir, self.state, lambda batch: self.store.add("node-a", batch.file, batch.lines))

    def stored(self) -> list[tuple[str, int, str]]:
        return self.store._db.execute("SELECT file, line, event FROM journal_event ORDER BY file, line").fetchall()

    def test_backfills_skips_chat_waits_for_whole_lines_and_resumes(self) -> None:
        self.write(FIRST, line("Fileheader", 0) + line("ReceiveText", 1, Message="hi") + line("Undocked", 2)
                   + "not json\n" + line("Friends", 3, Name="x"))
        self.write("Journal.2026-11-10T080000.01.txt", line("Docked", 4))  # not a journal file
        # The game is still writing the last line.
        self.write(SECOND, line("LoadGame", 5) + line("Docked", 6)[:20])

        # The bad line is passed on too; the store leaves it out.
        self.assertEqual(self.sync(), 4)
        self.assertEqual(self.stored(), [(FIRST, 1, "Fileheader"), (FIRST, 3, "Undocked"), (SECOND, 1, "LoadGame")])
        self.assertEqual(load_positions(self.state)[FIRST].line, 5)

        self.assertEqual(self.sync(), 0)
        self.write(SECOND, line("Docked", 6)[20:] + line("SendText", 7, Message="o7"))
        self.assertEqual(self.sync(), 1)
        self.assertEqual(self.stored()[-1], (SECOND, 2, "Docked"))

        # A lost state file passes everything on again; the store keeps one copy.
        self.state.unlink()
        self.assertEqual(self.sync(), 5)
        self.assertEqual(len(self.stored()), 4)
        self.assertEqual(self.store.counts()[0][0], "node-a")

    def test_batches_split_long_files_and_keep_line_numbers(self) -> None:
        self.write(FIRST, "".join(line("Music", i) for i in range(5)))
        batches = list(read_batches(self.dir, {}, batch_lines=2))
        self.assertEqual([[item.line for item in batch.lines] for batch in batches], [[1, 2], [3, 4], [5]])
        self.assertEqual(batches[-1].position, SyncPosition(5, (self.dir / FIRST).stat().st_size))
        self.assertEqual(list(read_batches(self.dir, {FIRST: batches[-1].position})), [])


if __name__ == "__main__":
    unittest.main()
