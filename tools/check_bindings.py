from __future__ import annotations

import argparse
import json
import sys

from edap.binding_lookup import load_binding_lookup
from edap.bindings import AUTOPILOT_OPTIONAL_BINDINGS, AUTOPILOT_REQUIRED_BINDINGS, REQUIRED_BINDINGS
from edap.config import ConfigError, DEFAULT_CONFIG_PATH
from edap.runtime import build_runtime_context, load_config_with_fallback


def main() -> int:
    parser = argparse.ArgumentParser(description="Check whether required Elite bindings are available")
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to config TOML file",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit full JSON output",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show supported and optional bindings in plain-text output",
    )
    args = parser.parse_args()

    try:
        loaded = load_config_with_fallback(args.config)
    except FileNotFoundError:
        sys.stderr.write(
            f"Config file not found: {args.config}\n"
            "Create a `config.toml` with the overrides you need, use `config.example.toml` as a reference, "
            "or pass `--config /path/to/config.toml`.\n"
        )
        return 2
    except ConfigError as exc:
        sys.stderr.write(f"Invalid config: {exc}\n")
        return 2

    runtime = build_runtime_context(loaded.config)
    bindings_file = runtime.bindings.effective_path
    bindings_source = runtime.bindings.cli_source_status()
    if bindings_file is None:
        sys.stderr.write(
            "Could not resolve bindings file. "
            f"Source status: {bindings_source}. Configure `paths.bindings_file` or ensure CrossOver auto-detection works.\n"
        )
        return 2

    try:
        lookup = load_binding_lookup(bindings_file, actions=REQUIRED_BINDINGS)
    except Exception as exc:
        sys.stderr.write(f"Could not load bindings from {bindings_file}: {exc}\n")
        return 2

    supported_all = {
        action: binding.to_dict()
        for action, binding in sorted(lookup.supported_actions().items())
    }
    issues_all = {
        action: result.to_dict()
        for action, result in sorted(lookup.issues().items())
    }
    required_supported = {
        action: binding
        for action, binding in supported_all.items()
        if action in AUTOPILOT_REQUIRED_BINDINGS
    }
    required_issues = {
        action: result
        for action, result in issues_all.items()
        if action in AUTOPILOT_REQUIRED_BINDINGS
    }
    optional_supported = {
        action: binding
        for action, binding in supported_all.items()
        if action in AUTOPILOT_OPTIONAL_BINDINGS
    }
    optional_issues = {
        action: result
        for action, result in issues_all.items()
        if action in AUTOPILOT_OPTIONAL_BINDINGS
    }

    payload = {
        "config_path": loaded.config_path,
        "used_example_config_fallback": loaded.used_example_config_fallback,
        "bindings_file": str(bindings_file),
        "bindings_source": bindings_source,
        "required_count": len(AUTOPILOT_REQUIRED_BINDINGS),
        "resolved_count": len(required_supported),
        "issue_count": len(required_issues),
        "ok": len(required_issues) == 0,
        "supported": required_supported,
        "issues": required_issues,
        "optional_supported": optional_supported,
        "optional_issues": optional_issues,
        "all_supported": supported_all,
        "all_issues": issues_all,
    }
    if args.json:
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        _print_summary(payload, verbose=args.verbose)
    return 0 if payload["ok"] else 1


def _print_summary(payload: dict[str, object], *, verbose: bool) -> None:
    bindings_file = payload["bindings_file"]
    resolved_count = payload["resolved_count"]
    required_count = payload["required_count"]
    ok = payload["ok"]
    issues = payload["issues"]
    optional_supported = payload["optional_supported"]
    optional_issues = payload["optional_issues"]

    status = "OK" if ok else "MISSING"
    sys.stdout.write(f"Bindings check: {status} ({resolved_count}/{required_count} required)\n")
    sys.stdout.write(f"Bindings file: {bindings_file}\n")

    if issues:
        sys.stdout.write("Required issues:\n")
        for action, result in issues.items():
            reason = result.get("reason", result.get("status", "unknown"))
            sys.stdout.write(f"- {action}: {reason}\n")
    else:
        sys.stdout.write("All required autopilot bindings are present.\n")

    if verbose:
        if optional_supported or optional_issues:
            sys.stdout.write("Optional bindings:\n")
            for action, binding in optional_supported.items():
                modifier = binding.get("modifier")
                if modifier:
                    sys.stdout.write(f"- {action}: {binding['key']} + {modifier}\n")
                else:
                    sys.stdout.write(f"- {action}: {binding['key']}\n")
            for action, result in optional_issues.items():
                reason = result.get("reason", result.get("status", "unknown"))
                sys.stdout.write(f"- {action}: {reason}\n")


if __name__ == "__main__":
    raise SystemExit(main())
