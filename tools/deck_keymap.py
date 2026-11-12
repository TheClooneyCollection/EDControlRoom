from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from edcr.binding_editor import apply_slot_change, parse_bindings_tree, write_bindings
from edcr.config import ConfigError, DEFAULT_CONFIG_PATH
from edcr.deck_keymap import DECK_KEYMAP, plan_deck_keymap
from edcr.runtime import build_runtime_context, load_config_with_fallback


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Add the keyboard keys EDControlRoom routines press to a controller preset "
            "(Steam Deck). Shows the plan unless --write is given."
        )
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Path to config TOML file")
    parser.add_argument(
        "--bindings-file",
        default=None,
        help="Override bindings file path (otherwise resolved through config)",
    )
    parser.add_argument("--write", action="store_true", help="Apply the plan (backs the file up first, never over an older backup)")
    args = parser.parse_args(argv)

    if args.bindings_file is not None:
        bindings_path = Path(args.bindings_file)
    else:
        try:
            loaded = load_config_with_fallback(args.config)
        except FileNotFoundError:
            sys.stderr.write(f"Config file not found: {args.config}\nPass --bindings-file or create a config.toml.\n")
            return 2
        except ConfigError as exc:
            sys.stderr.write(f"Invalid config: {exc}\n")
            return 2
        runtime = build_runtime_context(loaded.config, actions=[entry.action for entry in DECK_KEYMAP])
        resolved = runtime.bindings.effective_path
        if resolved is None:
            sys.stderr.write(
                f"Could not resolve bindings file. Source status: {runtime.bindings.cli_source_status()}.\n"
            )
            return 2
        bindings_path = resolved

    tree = parse_bindings_tree(bindings_path)
    steps = plan_deck_keymap(tree.getroot())
    print(f"Bindings file: {bindings_path}")
    for step in steps:
        print(f"  {step.status:<14} {step.action:<24} {step.detail}")

    changes = [step.change for step in steps if step.change is not None]
    if not changes:
        print("Nothing to change.")
        return 0
    if not args.write:
        print(f"{len(changes)} change(s) planned. Close Elite, then rerun with --write to apply.")
        return 0

    for change in changes:
        apply_slot_change(tree, change)
    backup_path = _unused_backup_path(bindings_path)
    shutil.copy2(bindings_path, backup_path)
    write_bindings(tree, bindings_path, backup=False)
    print(f"Wrote {len(changes)} change(s). Backup: {backup_path}")
    print("Start Elite again (do not save controls while it was open) and run tools/check_bindings.py.")
    return 0


def _unused_backup_path(path: Path) -> Path:
    # Never overwrite an earlier backup: the first one is usually the original preset.
    candidate = path.with_name(path.name + ".bak")
    index = 1
    while candidate.exists():
        candidate = path.with_name(f"{path.name}.bak.{index}")
        index += 1
    return candidate


if __name__ == "__main__":
    raise SystemExit(main())
