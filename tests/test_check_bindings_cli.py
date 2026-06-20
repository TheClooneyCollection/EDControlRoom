from __future__ import annotations

import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import check_bindings
from edap.binding_lookup import build_binding_lookup
from edap.bindings import Binding
from edap.config import load_config
from edap.runtime import LoadedConfig


class CheckBindingsCliTests(unittest.TestCase):
    def test_main_emits_json_supported_and_issues(self) -> None:
        loaded = LoadedConfig(
            config=load_config("config.example.toml"),
            config_path="config.example.toml",
            used_example_config_fallback=True,
        )
        runtime = type(
            "_Runtime",
            (),
            {
                "bindings": type(
                    "_Bindings",
                    (),
                    {
                        "effective_path": Path("/tmp/Custom.binds"),
                        "cli_source_status": staticmethod(lambda: "auto_detected"),
                    },
                )(),
            },
        )()
        lookup = build_binding_lookup(
            bindings={"SetSpeedZero": Binding(key="X"), "PrimaryFire": Binding(key="Space")},
            missing_actions={"UI_Back": "action is not present in bindings file", "MouseReset": "action is not present in bindings file"},
            actions=["SetSpeedZero", "UI_Back", "PrimaryFire", "MouseReset"],
        )

        with patch("tools.check_bindings.load_config_with_fallback", return_value=loaded), patch(
            "tools.check_bindings.build_runtime_context",
            return_value=runtime,
        ), patch("tools.check_bindings.load_binding_lookup", return_value=lookup), patch(
            "tools.check_bindings.REQUIRED_BINDINGS",
            ["SetSpeedZero", "UI_Back", "PrimaryFire", "MouseReset"],
        ), patch(
            "tools.check_bindings.AUTOPILOT_REQUIRED_BINDINGS",
            ["SetSpeedZero", "UI_Back"],
        ), patch(
            "tools.check_bindings.AUTOPILOT_OPTIONAL_BINDINGS",
            ["PrimaryFire", "MouseReset"],
        ), patch("sys.stdout", new_callable=io.StringIO) as stdout, patch(
            "sys.stderr", new_callable=io.StringIO
        ):
            with patch("sys.argv", ["tools/check_bindings.py", "--json"]):
                exit_code = check_bindings.main()

        self.assertEqual(exit_code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["required_count"], 2)
        self.assertEqual(payload["resolved_count"], 1)
        self.assertEqual(payload["issue_count"], 1)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["supported"]["SetSpeedZero"], {"key": "x", "modifier": None})
        self.assertEqual(payload["issues"]["UI_Back"]["status"], "missing")
        self.assertEqual(payload["optional_supported"]["PrimaryFire"], {"key": "space", "modifier": None})
        self.assertEqual(payload["optional_issues"]["MouseReset"]["status"], "missing")

    def test_main_emits_plain_text_summary_by_default(self) -> None:
        loaded = LoadedConfig(
            config=load_config("config.example.toml"),
            config_path="config.example.toml",
            used_example_config_fallback=True,
        )
        runtime = type(
            "_Runtime",
            (),
            {
                "bindings": type(
                    "_Bindings",
                    (),
                    {
                        "effective_path": Path("/tmp/Custom.binds"),
                        "cli_source_status": staticmethod(lambda: "auto_detected"),
                    },
                )(),
            },
        )()
        lookup = build_binding_lookup(
            bindings={"SetSpeedZero": Binding(key="X")},
            missing_actions={"UI_Back": "action is not present in bindings file"},
            actions=["SetSpeedZero", "UI_Back"],
        )

        with patch("tools.check_bindings.load_config_with_fallback", return_value=loaded), patch(
            "tools.check_bindings.build_runtime_context",
            return_value=runtime,
        ), patch("tools.check_bindings.load_binding_lookup", return_value=lookup), patch(
            "tools.check_bindings.REQUIRED_BINDINGS",
            ["SetSpeedZero", "UI_Back"],
        ), patch(
            "tools.check_bindings.AUTOPILOT_REQUIRED_BINDINGS",
            ["SetSpeedZero", "UI_Back"],
        ), patch(
            "tools.check_bindings.AUTOPILOT_OPTIONAL_BINDINGS",
            [],
        ), patch("sys.stdout", new_callable=io.StringIO) as stdout, patch(
            "sys.stderr", new_callable=io.StringIO
        ):
            with patch("sys.argv", ["tools/check_bindings.py"]):
                exit_code = check_bindings.main()

        self.assertEqual(exit_code, 1)
        self.assertIn("Bindings check: MISSING (1/2 required)", stdout.getvalue())
        self.assertIn("- UI_Back: action is not present in bindings file", stdout.getvalue())
        self.assertNotIn("supported", stdout.getvalue())

    def test_main_returns_error_when_bindings_file_cannot_be_resolved(self) -> None:
        loaded = LoadedConfig(
            config=load_config("config.example.toml"),
            config_path="config.example.toml",
            used_example_config_fallback=True,
        )
        runtime = type(
            "_Runtime",
            (),
            {
                "bindings": type(
                    "_Bindings",
                    (),
                    {
                        "effective_path": None,
                        "cli_source_status": staticmethod(lambda: "auto_detect_not_found"),
                    },
                )(),
            },
        )()

        with patch("tools.check_bindings.load_config_with_fallback", return_value=loaded), patch(
            "tools.check_bindings.build_runtime_context",
            return_value=runtime,
        ), patch("sys.stdout", new_callable=io.StringIO), patch(
            "sys.stderr", new_callable=io.StringIO
        ) as stderr:
            with patch("sys.argv", ["tools/check_bindings.py"]):
                exit_code = check_bindings.main()

        self.assertEqual(exit_code, 2)
        self.assertIn("Could not resolve bindings file.", stderr.getvalue())
