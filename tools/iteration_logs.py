from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from edap.iteration_logs import (
    LEGACY_SESSION_BASELINE,
    create_iteration_log,
    iter_iteration_log_paths,
    next_iteration_number,
    render_iteration_archive,
    validate_iteration_logs,
)

DEFAULT_LOGS_DIR = REPO_ROOT / "docs" / "iteration-logs"
DEFAULT_ARCHIVE_PATH = REPO_ROOT / "docs" / "iteration-archive.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manage per-iteration docs and the generated iteration archive."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    new_parser = subparsers.add_parser(
        "new",
        help="Create a new iteration log scaffold in docs/iteration-logs/.",
    )
    new_parser.add_argument("area", help="Short kebab-case area slug, e.g. docs or control-room.")
    new_parser.add_argument("title", help="Short kebab-case title slug.")
    new_parser.add_argument(
        "--timestamp",
        default=datetime.now().strftime("%Y-%m-%d-%H-%M"),
        help="Override timestamp in YYYY-MM-DD-HH-MM format.",
    )
    new_parser.add_argument(
        "--logs-dir",
        type=Path,
        default=DEFAULT_LOGS_DIR,
        help="Directory to create the log in. Default: docs/iteration-logs/",
    )

    render_parser = subparsers.add_parser(
        "render-archive",
        help="Generate docs/iteration-archive.md from docs/iteration-logs/.",
    )
    render_parser.add_argument(
        "--logs-dir",
        type=Path,
        default=DEFAULT_LOGS_DIR,
        help="Directory containing iteration logs. Default: docs/iteration-logs/",
    )
    render_parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_ARCHIVE_PATH,
        help="Archive path to write. Default: docs/iteration-archive.md",
    )
    render_parser.add_argument(
        "--baseline",
        type=int,
        default=LEGACY_SESSION_BASELINE,
        help="Legacy manual session number used as the pre-migration baseline.",
    )

    next_parser = subparsers.add_parser(
        "next-number",
        help="Print the next derived iteration number without writing any files.",
    )
    next_parser.add_argument(
        "--logs-dir",
        type=Path,
        default=DEFAULT_LOGS_DIR,
        help="Directory containing iteration logs. Default: docs/iteration-logs/",
    )
    next_parser.add_argument(
        "--baseline",
        type=int,
        default=LEGACY_SESSION_BASELINE,
        help="Legacy manual session number used as the pre-migration baseline.",
    )

    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate all iteration log filenames under docs/iteration-logs/.",
    )
    validate_parser.add_argument(
        "--logs-dir",
        type=Path,
        default=DEFAULT_LOGS_DIR,
        help="Directory containing iteration logs. Default: docs/iteration-logs/",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.command == "new":
        path = create_iteration_log(
            logs_dir=args.logs_dir,
            timestamp=args.timestamp,
            area=args.area,
            title=args.title,
        )
        print(path)
        return 0

    if args.command == "render-archive":
        archive = render_iteration_archive(logs_dir=args.logs_dir, baseline=args.baseline)
        args.output.write_text(archive, encoding="utf-8")
        print(args.output)
        return 0

    if args.command == "next-number":
        print(next_iteration_number(logs_dir=args.logs_dir, baseline=args.baseline))
        return 0

    if args.command == "validate":
        errors = validate_iteration_logs(logs_dir=args.logs_dir)
        if errors:
            for error in errors:
                print(f"{error.path}: {error.message}", file=sys.stderr)
            return 1
        print(f"validated {len(iter_iteration_log_paths(args.logs_dir))} iteration log files")
        return 0

    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
