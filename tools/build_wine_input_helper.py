"""Cross-compile the Wine input helper; never installs or launches it."""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
from collections.abc import Callable, Sequence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "build/wine_input_helper/edap_input_helper.exe"
DEFAULT_COMPILER = "/opt/homebrew/bin/x86_64-w64-mingw32-gcc"


def build_helper(compiler: str, output: Path, *, runner: Callable[..., object]) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    runner([compiler, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
            str(ROOT / "tools/wine_input_helper/edap_input_helper.c"),
            "-o", str(output), "-lws2_32", "-luser32"], check=True)
    return output


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", default=DEFAULT_COMPILER,
                        help="Compiler path or executable name on PATH")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    print(build_helper(args.compiler, args.output, runner=subprocess.run))


if __name__ == "__main__":
    main()
