"""Listen to the EDDN relay and keep the local market price database current."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from edap.config import load_config
from edap.eddn.listener import EddnListener, open_zmq_socket
from edap.eddn.service import status_line
from edap.eddn.store import EddnStore


def main(argv: list[str] | None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, help="Override eddn.database_file")
    parser.add_argument("--relay", help="Override eddn.relay")
    parser.add_argument("--max-age-days", type=float, help="Override eddn.max_age_days")
    parser.add_argument("--status-every", type=float, default=30.0, help="Seconds between status lines")
    args = parser.parse_args(argv)
    eddn = load_config().eddn
    relay = args.relay or eddn.relay
    store = EddnStore.open(args.db or eddn.database_file)
    listener = EddnListener(
        store=store,
        open_socket=lambda: open_zmq_socket(relay),
        time_fn=time.time,
        max_age_s=(args.max_age_days or eddn.max_age_days) * 86400,
        log=print,
    )
    print(f"Listening to {relay}; Ctrl-C to stop.")
    listener.start()
    try:
        while True:
            time.sleep(args.status_every)
            print(status_line(listener.stats(), store.counts()), flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        listener.stop()
        try:
            listener.join(5.0)
        except KeyboardInterrupt:
            # A second Ctrl-C (uv forwards one too) only cuts the wait short.
            pass
        store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
