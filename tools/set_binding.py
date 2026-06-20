from __future__ import annotations

import argparse
import json
import sys

from edap.binding_editor import (
    SlotChange,
    apply_slot_change,
    describe_binding,
    parse_bindings_tree,
    write_bindings,
)
from edap.config import ConfigError, DEFAULT_CONFIG_PATH
from edap.runtime import build_runtime_context, load_config_with_fallback


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Set, clear, or show an Elite Dangerous keyboard binding"
    )
    parser.add_argument("action", help="Elite action name, e.g. PitchDownButton")
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to config TOML file",
    )
    parser.add_argument(
        "--bindings-file",
        default=None,
        help="Override bindings file path (otherwise resolved through config)",
    )
    parser.add_argument(
        "--slot",
        choices=("primary", "secondary"),
        default="primary",
        help="Which slot to write (default: primary)",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--key", default=None, help="Key to bind (internal name, e.g. '.', 'a', 'left_shift')")
    mode.add_argument("--clear", action="store_true", help="Clear the slot instead of setting")
    mode.add_argument("--show", action="store_true", help="Show current bindings for the action and exit")
    parser.add_argument("--modifier", default=None, help="Optional modifier (e.g. ctrl, shift, left_alt)")
    parser.add_argument("--no-backup", action="store_true", help="Skip writing a .bak alongside the bindings file")
    args = parser.parse_args()

    bindings_path_str = args.bindings_file
    if bindings_path_str is None:
        try:
            loaded = load_config_with_fallback(args.config)
        except FileNotFoundError:
            sys.stderr.write(
                f"Config file not found: {args.config}\n"
                f"Pass --bindings-file or create a config.toml.\n"
            )
            return 2
        except ConfigError as exc:
            sys.stderr.write(f"Invalid config: {exc}\n")
            return 2

        runtime = build_runtime_context(loaded.config, actions=[args.action])
        bindings_file = runtime.bindings.effective_path
        if bindings_file is None:
            sys.stderr.write(
                "Could not resolve bindings file. "
                f"Source status: {runtime.bindings.cli_source_status()}.\n"
            )
            return 2
        resolved_path = bindings_file
    else:
        from pathlib import Path

        resolved_path = Path(bindings_path_str)

    tree = parse_bindings_tree(resolved_path)

    if args.show or (args.key is None and not args.clear):
        payload = {
            "bindings_file": str(resolved_path),
            "binding": describe_binding(tree, args.action),
        }
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    slot = args.slot.capitalize()
    try:
        change = SlotChange(
            action=args.action,
            slot=slot,
            key=None if args.clear else args.key,
            modifier=None if args.clear else args.modifier,
        )
        diff = apply_slot_change(tree, change)
    except ValueError as exc:
        sys.stderr.write(f"Invalid change: {exc}\n")
        return 2

    backup_path = write_bindings(tree, resolved_path, backup=not args.no_backup)

    payload = {
        "bindings_file": str(resolved_path),
        "backup_file": str(backup_path) if backup_path is not None else None,
        "slot": slot,
        "diff": diff,
    }
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
