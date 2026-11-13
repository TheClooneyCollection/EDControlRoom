from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from edcr.config import ConfigError, default_runtime_platform, load_config, save_home_system, save_piper_voice
from edcr.eddn.routes import TimeModel


def _write_config(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


class LoadConfigTests(unittest.TestCase):
    def test_buy_top_up_limit_accepts_zero_and_flat_aliases_and_rejects_negative(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            for key in ("market_buy_top_up_max_attempts", '"market.buy_top_up_max_attempts"'):
                for value in (0, 4, -1):
                    with self.subTest(key=key, value=value):
                        _write_config(path, f"[controls]\n{key} = {value}\n")
                        if value < 0:
                            with self.assertRaisesRegex(ConfigError, "market_buy_top_up_max_attempts"):
                                load_config(path)
                        else:
                            self.assertEqual(load_config(path).controls.market_buy_top_up_max_attempts, value)

    def test_loads_valid_config_with_defaults(self) -> None:
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "config.toml"
            _write_config(
                config_path,
                """
[paths]

[controls]

[runtime]
""".strip(),
            )

            with patch("edcr.config.default_runtime_platform", return_value="macos"):
                config = load_config(config_path)

            self.assertIsNone(config.paths.journal_dir)
            self.assertIsNone(config.paths.bindings_file)
            self.assertEqual(config.controls.start_hotkey, "home")
            self.assertEqual(config.controls.market_buy_top_up_max_attempts, 3)
            self.assertEqual(config.controls.stop_hotkey, "end")
            self.assertEqual(config.controls.minimum_action_hold_seconds, 0.1)
            self.assertEqual(config.controls.continuous_action_hold_seconds, 0.2)
            self.assertEqual(config.controls.galaxy_map_settle_seconds, 2.0)
            self.assertEqual(config.controls.dock_supercruise_exit_settle_seconds, 3.0)
            self.assertEqual(config.controls.haul_dock_timeout_seconds, 1200.0)
            self.assertEqual(config.controls.undock_timeout_seconds, 30.0)
            self.assertEqual(config.controls.undock_no_track_timeout_seconds, 600.0)
            self.assertEqual(config.controls.market_buy_max_hold_seconds, 20.0)
            self.assertEqual(len(config.controls.market_buy_hold_segments), 1)
            self.assertEqual(config.controls.market_buy_hold_segments[0].start, 0)
            self.assertEqual(config.controls.market_buy_hold_segments[0].function, "flat")
            self.assertEqual(config.controls.market_buy_hold_segments[0].hold_seconds, 3.5)
            self.assertEqual(config.controls.market_sell_quantity_restore_taps, 5)
            self.assertEqual(config.controls.market_sell_quantity_restore_tap_delay_seconds, 0.05)
            self.assertEqual(config.controls.market_critical_level_multiplier, 10.0)
            self.assertTrue(config.controls.haul_two_way_auto_hyperspace_engage)
            self.assertTrue(config.controls.haul_two_way_open_nav_panel_after_hyperspace_arrival)
            self.assertEqual(config.controls.haul_two_way_nav_panel_open_delay_seconds, 3.0)
            self.assertEqual(config.runtime.platform, "macos")
            self.assertTrue(config.timing.enabled)
            self.assertEqual(config.timing.distribution, "log_normal")
            self.assertEqual(config.timing.delay.sigma, 0.18)
            self.assertEqual(config.timing.delay.min_factor, 0.85)
            self.assertEqual(config.timing.delay.max_factor, 1.35)
            self.assertEqual(config.timing.hold.min_seconds, 0.02)
            self.assertEqual(config.timing.typing.max_factor, 1.75)
            self.assertEqual(config.control_room.state_file, Path(".control_room_state.json"))
            self.assertEqual(config.control_room.haul_runs_file, Path(".control_room_haul_runs.jsonl"))
            self.assertEqual(config.control_room.history_limit, 20)
            self.assertEqual(config.control_room.activity_log_max_lines, 2000)
            self.assertEqual(config.control_room.command_delay_seconds, 5.0)
            self.assertEqual(config.control_room.status_refresh_seconds, 2.0)
            self.assertTrue(config.control_room.check_for_updates)
            self.assertEqual(config.control_room.home_system, "")
            self.assertFalse(config.control_room.clear_session_on_launch)
            self.assertEqual(config.control_room.route_compare_navroute_wait_seconds, 6.0)
            self.assertEqual(config.control_room.route_compare_compare_retry_attempts, 3)
            self.assertEqual(config.control_room.recent_markets_limit, 20)
            self.assertTrue(config.control_room.lan_also_localhost)
            self.assertTrue(config.tts.enabled)
            self.assertEqual(config.tts.title_mode, "commander_name")
            self.assertEqual(config.tts.title, "commander")
            self.assertEqual(config.tts.phrases["destination_set"], "Opening galaxy map to set destination to {system_name}.")
            self.assertEqual(config.tts.phrases["fsd_target_locked"], "New FSD target acquired: {system_name}.")
            self.assertEqual(
                config.tts.phrases["auto_docking_engaged"],
                "Engaging auto docking sequence.",
            )
            self.assertEqual(
                config.tts.phrases["ship_serviced"],
                "Ship is fully fueled up and repaired, {title}.",
            )
            self.assertEqual(
                config.tts.phrases["docking_pad_full"],
                "Docking denied at {station_name}. Pads are full. Holding position and retrying.",
            )
            self.assertEqual(
                config.tts.phrases["haul_cargo_state_stale"],
                "{title}, cargo hold already has {cargo_count} tonnes, but cargo details are stale. "
                "Please relog, then resume haul.",
            )
            self.assertEqual(
                config.tts.phrases["haul_unrelated_cargo_loaded"],
                "{title}, unrelated cargo is already loaded: {cargo_summary}. "
                "Selling cargo before continuing haul.",
            )
            self.assertEqual(config.tts.phrases["selling_all_cargo"], "Selling all cargo.")
            self.assertEqual(config.tts.phrases["market_buy_none_available"],
                             "{title}, no {commodity_name} available to buy. Continuing with current load.")
            self.assertEqual(config.tts.phrases["haul_top_up_unaffordable"],
                             "{title}, cannot afford more {commodity_name} at {station_name}. Continuing with partial load.")
            self.assertEqual(config.tts.phrases["haul_buy_still_short"],
                             "{title}, buy short at {station_name}. Continuing with partial load.")
            self.assertEqual(
                config.tts.phrases["haul_pause_requested"],
                "Roger {title}, we will pause hauling at the next station.",
            )
            self.assertEqual(
                config.tts.phrases["haul_paused"],
                "{title}, haul paused at station {station_index}.",
            )
            self.assertEqual(
                config.error_messages.templates["station_mismatch_message"],
                "Station mismatch: market data indicates {market_station}, but we are docked at {docked_station}.",
            )
            self.assertEqual(
                config.messages.templates["dest_usage"],
                "Usage: dest <system name>",
            )

    def test_error_message_partial_override_keeps_default_templates(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            _write_config(
                config_path,
                """
[paths]

[controls]

[runtime]

[error_messages.templates.station_mismatch]
message = "Market data says {market_station}; docked station says {docked_station}."
""".strip(),
            )

            config = load_config(config_path)

            self.assertEqual(
                config.error_messages.templates["station_mismatch_message"],
                "Market data says {market_station}; docked station says {docked_station}.",
            )
            self.assertEqual(
                config.error_messages.templates["route_mismatch_suggestion"],
                "Use Ctrl-R then e to edit the destination or haul parameters, or start a new haul with the correct route.",
            )

    def test_message_partial_override_keeps_default_templates(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            _write_config(
                config_path,
                """
[paths]

[controls]

[runtime]

[messages.templates]
dest_usage = "Usage: dest <system or station name>"
""".strip(),
            )

            config = load_config(config_path)

            self.assertEqual(
                config.messages.templates["dest_usage"],
                "Usage: dest <system or station name>",
            )
            self.assertEqual(
                config.messages.templates["invalid_amount"],
                "Invalid amount. Use a positive integer or MAX.",
            )

    def test_eddn_time_model_overrides_single_fields_and_rejects_bad_keys(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            _write_config(path, "[paths]\n[controls]\n[runtime]\n")
            self.assertEqual(load_config(path).eddn.time_model, TimeModel())

            _write_config(path, "[eddn.time_model]\ndocked_s = 60\nfirst_jump_s = 140.0\n")
            self.assertEqual(
                load_config(path).eddn.time_model, replace(TimeModel(), docked_s=60.0, first_jump_s=140.0)
            )

            for body, message in (
                ("docked = 60", "Unknown `eddn.time_model` keys: docked"),
                ("docked_s = -1", "eddn.time_model.docked_s"),
                ('docked_s = "60"', "docked_s"),
            ):
                with self.subTest(body=body):
                    _write_config(path, f"[eddn.time_model]\n{body}\n")
                    with self.assertRaisesRegex(ConfigError, message):
                        load_config(path)

    def test_loads_control_room_home_system_override(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            _write_config(
                config_path,
                """
[paths]

[controls]

[runtime]

[control_room]
home_system = "Achenar"
haul_runs_file = 'custom-runs.jsonl'
""".strip(),
            )

            config = load_config(config_path)

            self.assertEqual(config.control_room.home_system, "Achenar")
            self.assertEqual(config.control_room.haul_runs_file, Path("custom-runs.jsonl"))

    def test_loads_timing_override(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            _write_config(
                config_path,
                """
[paths]

[controls]

[runtime]

[timing]
enabled = false

[timing.hold]
sigma = 0.25
min_factor = 0.95
max_factor = 1.4
min_seconds = 0.03
""".strip(),
            )

            config = load_config(config_path)

            self.assertFalse(config.timing.enabled)
            self.assertEqual(config.timing.hold.sigma, 0.25)
            self.assertEqual(config.timing.hold.min_factor, 0.95)
            self.assertEqual(config.timing.hold.max_factor, 1.4)
            self.assertEqual(config.timing.hold.min_seconds, 0.03)
            self.assertEqual(config.timing.delay.sigma, 0.18)

    def test_loads_control_room_clear_session_on_launch_override(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            _write_config(
                config_path,
                """
[paths]

[controls]

[runtime]

[control_room]
clear_session_on_launch = true
""".strip(),
            )

            config = load_config(config_path)

            self.assertTrue(config.control_room.clear_session_on_launch)

    def test_save_home_system_updates_existing_control_room_section(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            _write_config(
                config_path,
                """
[paths]

[controls]

[runtime]

[control_room]
command_delay_seconds = 5.0
""".strip() + "\n",
            )

            save_home_system(config_path, "Shinrarta Dezhra")

            saved = config_path.read_text(encoding="utf-8")
            self.assertIn('home_system = "Shinrarta Dezhra"', saved)
            self.assertIn("command_delay_seconds = 5.0", saved)
            self.assertEqual(load_config(config_path).control_room.home_system, "Shinrarta Dezhra")

    def test_save_home_system_creates_minimal_valid_config_when_missing(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"

            save_home_system(config_path, "Sol")

            self.assertTrue(config_path.exists())
            config = load_config(config_path)
            self.assertEqual(config.control_room.home_system, "Sol")

    def test_legacy_flat_error_message_override_still_loads(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            _write_config(
                config_path,
                """
[paths]

[controls]

[runtime]

[error_messages.templates]
route_mismatch_suggestion = "Retry with the corrected route."
""".strip(),
            )

            config = load_config(config_path)

            self.assertEqual(
                config.error_messages.templates["route_mismatch_suggestion"],
                "Retry with the corrected route.",
            )

    def test_tts_partial_override_keeps_default_phrases(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            _write_config(
                config_path,
                """
[paths]

[controls]

[runtime]

[tts]
title_mode = "custom"
title = "captain"
disabled_messages = ["arrival"]

[tts.phrases]
station_cleared = "Station cleared, {title}."
""".strip(),
            )

            config = load_config(config_path)

            self.assertEqual(config.tts.title_mode, "custom")
            self.assertEqual(config.tts.title, "captain")
            self.assertEqual(config.tts.disabled_messages, ("arrival",))
            self.assertEqual(config.tts.phrases["station_cleared"], "Station cleared, {title}.")
            self.assertEqual(
                config.tts.phrases["haul_aborted"],
                "Haul aborted.",
            )
            self.assertEqual(config.tts.phrases["destination_set"], "Opening galaxy map to set destination to {system_name}.")

    def test_loads_nested_control_section_overrides(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            _write_config(
                config_path,
                """
[paths]

[controls]
start_hotkey = "pageup"

[controls.hold]
minimum_action_seconds = 0.15
continuous_action_seconds = 0.25

[controls.market]
nav_delay_seconds = 0.2
trade_max_attempts = 5
buy_top_up_max_attempts = 7

[controls.haul.two_way]
auto_hyperspace_engage = false
nav_panel_open_delay_seconds = 4.0

[runtime]
""".strip(),
            )

            config = load_config(config_path)

            self.assertEqual(config.controls.start_hotkey, "pageup")
            self.assertEqual(config.controls.minimum_action_hold_seconds, 0.15)
            self.assertEqual(config.controls.continuous_action_hold_seconds, 0.25)
            self.assertEqual(config.controls.market_nav_delay_seconds, 0.2)
            self.assertEqual(config.controls.market_trade_max_attempts, 5)
            self.assertEqual(config.controls.market_buy_top_up_max_attempts, 7)
            self.assertEqual(config.controls.market_buy_max_hold_seconds, 20.0)
            self.assertEqual(config.controls.market_buy_hold_segments[0].function, "flat")
            self.assertEqual(config.controls.market_sell_quantity_restore_taps, 5)
            self.assertFalse(config.controls.haul_two_way_auto_hyperspace_engage)
            self.assertEqual(config.controls.haul_two_way_nav_panel_open_delay_seconds, 4.0)

    def test_loads_control_room_update_check_override(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            _write_config(
                config_path,
                """
[paths]

[controls]

[runtime]

[control_room]
check_for_updates = false
""".strip(),
            )

            config = load_config(config_path)

            self.assertFalse(config.control_room.check_for_updates)

    def test_loads_control_room_activity_log_limit_override(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            _write_config(
                config_path,
                """
[paths]

[controls]

[runtime]

[control_room]
activity_log_max_lines = 500
""".strip(),
            )

            config = load_config(config_path)

            self.assertEqual(config.control_room.activity_log_max_lines, 500)

    def test_defaults_runtime_platform_from_host_when_omitted(self) -> None:
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "config.toml"
            _write_config(
                config_path,
                """
[paths]

[controls]

[runtime]
""".strip(),
            )

            with patch("edcr.config.default_runtime_platform", return_value="windows"):
                config = load_config(config_path)

            self.assertEqual(config.runtime.platform, "windows")

    def test_tts_commander_name_mode_allows_blank_custom_title(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            _write_config(
                config_path,
                """
[paths]

[controls]

[runtime]

[tts]
title_mode = "commander_name"
title = ""
""".strip(),
            )

            config = load_config(config_path)

            self.assertEqual(config.tts.title_mode, "commander_name")
            self.assertEqual(config.tts.title, "")

    def test_rejects_unknown_tts_title_mode(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            _write_config(
                config_path,
                """
[paths]

[controls]

[runtime]

[tts]
title_mode = "invalid"
""".strip(),
            )

            with self.assertRaisesRegex(ConfigError, "tts.title_mode"):
                load_config(config_path)

    def test_rejects_blank_custom_tts_title(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            _write_config(
                config_path,
                """
[paths]

[controls]

[runtime]

[tts]
title_mode = "custom"
title = ""
""".strip(),
            )

            with self.assertRaisesRegex(ConfigError, "tts.title"):
                load_config(config_path)

    def test_tts_piper_voice_needs_both_existing_files(self) -> None:
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "config.toml"
            executable = temp_path / "piper"
            model = temp_path / "voice.onnx"
            executable.write_text("", encoding="utf-8")
            base = "[paths]\n\n[controls]\n\n[runtime]\n\n[tts.piper]\n"

            _write_config(config_path, base + f"executable = '{executable}'\n")
            with self.assertRaisesRegex(ConfigError, "needs both `executable` and `model`"):
                load_config(config_path)

            _write_config(config_path, base + f"executable = '{executable}'\nmodel = '{model}'\n")
            with self.assertRaisesRegex(ConfigError, "tts.piper.model"):
                load_config(config_path)

            model.write_text("", encoding="utf-8")
            config = load_config(config_path)
            self.assertEqual(config.tts.piper.executable, executable)
            self.assertEqual(config.tts.piper.model, model)

    def test_tts_piper_tuning_loads_validates_and_saves(self) -> None:
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "config.toml"
            executable = temp_path / "piper"
            model = temp_path / "voice.onnx"
            executable.write_text("", encoding="utf-8")
            model.write_text("", encoding="utf-8")
            base = f"[paths]\n\n[controls]\n\n[runtime]\n\n[tts.piper]\nexecutable = '{executable}'\nmodel = '{model}'\n"

            _write_config(config_path, base + "length_scale = 0\n")
            with self.assertRaisesRegex(ConfigError, "tts.piper.length_scale"):
                load_config(config_path)
            _write_config(config_path, base + "volume = 'loud'\n")
            with self.assertRaisesRegex(ConfigError, "tts.piper.volume"):
                load_config(config_path)

            _write_config(config_path, base + "# tuned by hand\nvolume = 2\n\n[tts.phrases]\narrival = 'Here.'\n")
            voice = load_config(config_path).tts.piper
            self.assertEqual((voice.volume, voice.length_scale), (2.0, None))

            save_piper_voice(config_path, replace(voice, length_scale=0.85, noise_w_scale=0.6))

            saved = config_path.read_text(encoding="utf-8")
            self.assertIn("# tuned by hand", saved)
            reloaded = load_config(config_path)
            self.assertEqual(reloaded.tts.piper, replace(voice, length_scale=0.85, noise_w_scale=0.6))
            self.assertEqual(reloaded.tts.phrases["arrival"], "Here.")

    def test_rejects_omitted_runtime_platform_on_unsupported_host(self) -> None:
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "config.toml"
            _write_config(
                config_path,
                """
[paths]

[controls]

[runtime]
""".strip(),
            )

            with patch(
                "edcr.config.default_runtime_platform",
                side_effect=ConfigError("Config value `runtime.platform` must be set explicitly on this host."),
            ):
                with self.assertRaisesRegex(ConfigError, "runtime.platform"):
                    load_config(config_path)

    def test_default_runtime_platform_maps_supported_hosts(self) -> None:
        with patch("edcr.config.sys.platform", "darwin"):
            self.assertEqual(default_runtime_platform(), "macos")
        with patch("edcr.config.sys.platform", "linux"):
            self.assertEqual(default_runtime_platform(), "linux")
        with patch("edcr.config.sys.platform", "win32"):
            self.assertEqual(default_runtime_platform(), "windows")

    def test_default_runtime_platform_rejects_unsupported_host(self) -> None:
        with patch("edcr.config.sys.platform", "freebsd13"):
            with self.assertRaisesRegex(ConfigError, "runtime.platform"):
                default_runtime_platform()

    def test_rejects_non_positive_continuous_hold_setting(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            _write_config(
                config_path,
                """
[paths]

[controls]
continuous_action_hold_seconds = 0.0

[runtime]
""".strip(),
            )

            with self.assertRaisesRegex(ConfigError, "continuous_action_hold_seconds"):
                load_config(config_path)

    def test_rejects_non_positive_minimum_hold_setting(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            _write_config(
                config_path,
                """
[paths]

[controls]
minimum_action_hold_seconds = 0.0

[runtime]
""".strip(),
            )

            with self.assertRaisesRegex(ConfigError, "minimum_action_hold_seconds"):
                load_config(config_path)

    def test_rejects_continuous_hold_below_minimum_hold(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            _write_config(
                config_path,
                """
[paths]

[controls]
minimum_action_hold_seconds = 0.15
continuous_action_hold_seconds = 0.1

[runtime]
""".strip(),
            )

            with self.assertRaisesRegex(ConfigError, "continuous_action_hold_seconds"):
                load_config(config_path)

    def test_rejects_negative_control_room_command_delay(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            _write_config(
                config_path,
                """
[paths]

[controls]

[runtime]

[control_room]
command_delay_seconds = -0.1
""".strip(),
            )

            with self.assertRaisesRegex(ConfigError, "control_room.command_delay_seconds"):
                load_config(config_path)

    def test_rejects_unknown_timing_distribution(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            _write_config(
                config_path,
                """
[paths]

[controls]

[runtime]

[timing]
distribution = "uniform"
""".strip(),
            )

            with self.assertRaisesRegex(ConfigError, "timing.distribution"):
                load_config(config_path)

    def test_rejects_invalid_timing_factor_range(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            _write_config(
                config_path,
                """
[paths]

[controls]

[runtime]

[timing.delay]
min_factor = 1.2
max_factor = 1.1
""".strip(),
            )

            with self.assertRaisesRegex(ConfigError, "timing.delay.max_factor"):
                load_config(config_path)

    def test_rejects_negative_control_room_status_refresh(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            _write_config(
                config_path,
                """
[paths]

[controls]

[runtime]

[control_room]
status_refresh_seconds = -0.1
""".strip(),
            )

            with self.assertRaisesRegex(ConfigError, "control_room.status_refresh_seconds"):
                load_config(config_path)

    def test_rejects_non_positive_control_room_activity_log_limit(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            _write_config(
                config_path,
                """
[paths]

[controls]

[runtime]

[control_room]
activity_log_max_lines = 0
""".strip(),
            )

            with self.assertRaisesRegex(ConfigError, "control_room.activity_log_max_lines"):
                load_config(config_path)

    def test_rejects_non_positive_market_critical_level_multiplier(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            _write_config(
                config_path,
                """
[paths]

[controls]
market_critical_level_multiplier = 0

[runtime]
""".strip(),
            )

            with self.assertRaisesRegex(ConfigError, "market_critical_level_multiplier"):
                load_config(config_path)

    def test_rejects_market_buy_hold_segments_that_do_not_start_at_zero(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            _write_config(
                config_path,
                """
[paths]

[[controls.market.buy_hold_segments]]
start = 50
function = "flat"
hold_seconds = 1.0

[runtime]
""".strip(),
            )

            with self.assertRaisesRegex(ConfigError, "must start at 0"):
                load_config(config_path)

    def test_rejects_invalid_market_buy_hold_segment_function(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            _write_config(
                config_path,
                """
[paths]

[[controls.market.buy_hold_segments]]
start = 0
function = "curveball"

[runtime]
""".strip(),
            )

            with self.assertRaisesRegex(ConfigError, "buy_hold_segments\\[0\\]\\.function"):
                load_config(config_path)

    def test_rejects_non_positive_market_buy_max_hold_seconds(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            _write_config(
                config_path,
                """
[paths]

[controls.market]
buy_max_hold_seconds = 0

[runtime]
""".strip(),
            )

            with self.assertRaisesRegex(ConfigError, "market_buy_max_hold_seconds"):
                load_config(config_path)

    def test_loads_custom_market_buy_hold_segments(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            _write_config(
                config_path,
                """
[paths]

[[controls.market.buy_hold_segments]]
start = 0
function = "flat"
hold_seconds = 0.75

[[controls.market.buy_hold_segments]]
start = 25
function = "linear"
seconds_per_ton = 0.02

[[controls.market.buy_hold_segments]]
start = 250
function = "log"
base_seconds = -1.5
multiplier = 0.8

[runtime]
""".strip(),
            )

            config = load_config(config_path)

            self.assertEqual(len(config.controls.market_buy_hold_segments), 3)
            self.assertEqual(config.controls.market_buy_hold_segments[0].hold_seconds, 0.75)
            self.assertEqual(config.controls.market_buy_hold_segments[1].seconds_per_ton, 0.02)
            self.assertEqual(config.controls.market_buy_hold_segments[2].base_seconds, -1.5)

    def test_rejects_non_positive_market_buy_hold_segment_log_multiplier(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            _write_config(
                config_path,
                """
[paths]

[[controls.market.buy_hold_segments]]
start = 0
function = "log"
multiplier = 0

[runtime]
""".strip(),
            )

            with self.assertRaisesRegex(ConfigError, "buy_hold_segments\\[0\\]\\.multiplier"):
                load_config(config_path)

    def test_rejects_non_positive_market_sell_quantity_restore_taps(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            _write_config(
                config_path,
                """
[paths]

[controls.market]
sell_quantity_restore_taps = 0

[runtime]
""".strip(),
            )

            with self.assertRaisesRegex(ConfigError, "market_sell_quantity_restore_taps"):
                load_config(config_path)

    def test_ignores_legacy_screen_table(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            _write_config(
                config_path,
                """
[paths]

[controls]

[screen]
resolution_width = 2560

[screen.capture]
mode = "region"

[runtime]
""".strip(),
            )

            config = load_config(config_path)

            self.assertFalse(hasattr(config, "screen"))

    def test_rejects_unsupported_platform(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            _write_config(
                config_path,
                """
[paths]

[controls]

[runtime]
platform = "plan9"
""".strip(),
            )

            with self.assertRaisesRegex(ConfigError, "runtime.platform"):
                load_config(config_path)

    def test_rejects_existing_bindings_directory_when_file_expected(self) -> None:
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            bindings_dir = temp_path / "Bindings"
            bindings_dir.mkdir()
            config_path = temp_path / "config.toml"
            _write_config(
                config_path,
                f"""
[paths]
bindings_file = '{bindings_dir}'

[controls]

[runtime]
""".strip(),
            )

            with self.assertRaisesRegex(ConfigError, "paths.bindings_file"):
                load_config(config_path)

    def test_rejects_boolean_for_integer_setting(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            _write_config(
                config_path,
                """
[paths]

[controls]

[runtime]

[control_room]
history_limit = true
""".strip(),
            )

            with self.assertRaisesRegex(ConfigError, "history_limit"):
                load_config(config_path)

