"""Explicit operator command: copy a built helper into an existing bottle."""
from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from pathlib import Path
import shutil

DEFAULT_SOURCE = Path(__file__).resolve().parents[1] / "build/wine_input_helper/edcr_input_helper.exe"
DEFAULT_BOTTLES_DIR = Path.home() / "Library/Application Support/CrossOver/Bottles"


def install_helper(bottle: str, bottles_dir: Path, source: Path, *,
                   copy: Callable[[Path, Path], object]) -> Path:
    if not bottle or bottle in (".", "..") or any(c in bottle for c in "/\\"):
        raise ValueError("bottle must be a single directory name")
    root = bottles_dir.resolve()
    bottle_dir = root / bottle
    drive = bottle_dir / "drive_c"
    destination = drive / "edcr" / "edcr_input_helper.exe"
    # Refuse symlinks that escape the selected bottle or redirect its drive.
    if bottle_dir.resolve().parent != root or not drive.is_dir():
        raise ValueError("bottle must already exist and contain drive_c")
    if not destination.resolve().is_relative_to(bottle_dir.resolve()):
        raise ValueError("destination escapes the selected bottle")
    if not source.is_file():
        raise FileNotFoundError(f"build helper first: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    copy(source, destination)
    return destination


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bottle", required=True)
    parser.add_argument("--bottles-dir", type=Path, default=DEFAULT_BOTTLES_DIR)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args(argv)
    print(install_helper(args.bottle, args.bottles_dir, args.source, copy=shutil.copy2))


if __name__ == "__main__":
    main()
