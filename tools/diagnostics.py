from __future__ import annotations

import argparse
import json
import sys

from edap.config import ConfigError, DEFAULT_CONFIG_PATH
from edap.diagnostics import DiagnosticsOptions, run_diagnostics
from edap.runtime import load_config_with_fallback


def main() -> int:
    parser = argparse.ArgumentParser(description="EDAutopilot diagnostic runner")
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to config TOML file",
    )
    parser.add_argument(
        "--capture-screen",
        action="store_true",
        help="Capture a full-screen debug image using the configured resolution and scale",
    )
    parser.add_argument(
        "--send-test-key",
        action="store_true",
        help="Send a synthetic test key through the active input backend",
    )
    parser.add_argument(
        "--test-key",
        default="space",
        help="Key to send when --send-test-key is used",
    )
    parser.add_argument(
        "--test-modifier",
        default=None,
        help="Optional modifier to hold while sending the test key",
    )
    parser.add_argument(
        "--hold-seconds",
        type=float,
        default=0.0,
        help="Optional hold duration for the test key",
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=0.0,
        help="Delay before sending the test key so you can focus the game window",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Number of times to send the test key",
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
    options = DiagnosticsOptions(
        capture_screen=args.capture_screen,
        send_test_key=args.send_test_key,
        test_key=args.test_key,
        test_modifier=args.test_modifier,
        hold_s=args.hold_seconds,
        delay_s=args.delay_seconds,
        repeat=args.repeat,
    )
    result = run_diagnostics(loaded.config, options)
    result["config_path"] = loaded.config_path
    result["used_example_config_fallback"] = loaded.used_example_config_fallback

    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
