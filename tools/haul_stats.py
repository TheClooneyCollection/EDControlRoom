"""Query persisted haul runs without starting control room."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rich.console import Console

from edap.config import load_config
from edap.control_room.rendering import haul_history_summary_lines, journal_ledger_lines
from edap.journal_trade_ledger import journal_trade_ledger
from edap.runtime import build_game_paths, resolve_journal_path
from edap.haul_history import load_runs, parse_window, summarize
from edap.platform.local_time import SystemLocalTimezone


def main(argv: list[str] | None, *, now: datetime) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("window", nargs="*", help="today, 48h, week, month, all, or since YYYY-MM-DD")
    parser.add_argument("--json", action="store_true", help="Print a JSON summary")
    parser.add_argument("--file", type=Path, help="Override control_room.haul_runs_file")
    parser.add_argument("--journal-dir", type=Path, help="Override the configured journal directory")
    args = parser.parse_args(argv)
    try:
        since, until, label = parse_window(" ".join(args.window), now)
        config = None
        if args.file is None or args.journal_dir is None:
            try:
                config = load_config()
            except (ValueError, OSError):
                if args.file is None:
                    raise
        path = args.file if args.file is not None else config.control_room.haul_runs_file
        rows, skipped = load_runs(path)
        summary = summarize(rows, since, until, skipped_lines=skipped)
    except (ValueError, OSError) as exc:
        sys.stderr.write(f"{exc}\n")
        return 2
    journal_dir = args.journal_dir
    if journal_dir is None and config is not None:
        try:
            journal_dir = resolve_journal_path(config, game_paths=build_game_paths(config.runtime.platform)).effective_path
        except OSError:
            journal_dir = config.paths.journal_dir
    ledger = journal_trade_ledger(journal_dir, since, until)
    if args.json:
        payload = asdict(summary)
        payload["journal"] = asdict(ledger)
        print(json.dumps(payload, ensure_ascii=False, allow_nan=False))
    else:
        console = Console()
        if not rows:
            console.print("no haul runs recorded yet")
        for line in haul_history_summary_lines(summary, label) + journal_ledger_lines(ledger):
            console.print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(None, now=datetime.now(SystemLocalTimezone())))
