"""Write our own recent Market.json captures into the EDDN market database (newest data wins)."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from edap.config import load_config
from edap.eddn.game_markets import import_game_markets, import_summary
from edap.eddn.store import EddnStore


def main(argv: list[str] | None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, help="Override eddn.database_file")
    parser.add_argument("--recent-markets", type=Path, help="Override control_room.recent_markets_file")
    args = parser.parse_args(argv)
    config = load_config()
    # Safe beside a running server: the store waits for its short write lock.
    store = EddnStore.open(args.db or config.eddn.database_file)
    try:
        results = import_game_markets(store, args.recent_markets or config.control_room.recent_markets_file)
    finally:
        store.close()
    for result in results:
        print(f"{'written' if result.written else 'kept   '}  {result.station} ({result.system}) {result.timestamp}")
    print(import_summary(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
