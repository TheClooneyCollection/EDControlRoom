from __future__ import annotations

import unittest
from types import SimpleNamespace

from edap.actions import ActionDispatchResult
from edap.routines.hardpoints import retract_hardpoints_before_jump
from edap.routines.jump import jump
from edap.routines.transit import engage_hyperspace_after_escape
from tests.fakes import FakeShipControls, FakeWatcher


def status(deployed: bool):
    return SimpleNamespace(flags=SimpleNamespace(hardpoints_deployed=deployed))


class HardpointFlowTests(unittest.TestCase):
    def run_guard(self, states, *, clear_after=1, dispatch_ok=True):
        clock = [0.0]
        outputs = []
        current = [states[-1]]
        remaining = iter(states)

        def read():
            value = next(remaining, current[0])
            if isinstance(value, Exception):
                raise value
            return value

        def toggle():
            outputs.append("DeployHardpointToggle")
            if dispatch_ok and len(outputs) == clear_after:
                current[0] = status(False)
            return ActionDispatchResult(action="DeployHardpointToggle", status="ok" if dispatch_ok else "error", reason="missing binding" if not dispatch_ok else None)

        def sleep(seconds):
            clock[0] += seconds

        result = retract_hardpoints_before_jump(
            read_status_fn=read, toggle_fn=toggle, timeout_s=0.3,
            time_fn=lambda: clock[0], sleeper=sleep, progress_fn=lambda _: None,
        )
        return result, outputs, clock[0]

    def test_retracted_ship_is_left_untouched(self):
        result, outputs, elapsed = self.run_guard([status(False)])
        self.assertIsNone(result)
        self.assertEqual(outputs, [])
        self.assertEqual(elapsed, 0)

    def test_deployed_ship_waits_until_retraction_is_visible(self):
        result, outputs, elapsed = self.run_guard([status(True), status(True), status(False)])
        self.assertIsNone(result)
        self.assertEqual(outputs, ["DeployHardpointToggle"])
        self.assertGreater(elapsed, 0)

    def test_second_press_recovers_a_dropped_first_press(self):
        result, outputs, elapsed = self.run_guard([status(True)], clear_after=2)
        self.assertIsNone(result)
        self.assertEqual(outputs, ["DeployHardpointToggle"] * 2)
        self.assertGreaterEqual(elapsed, 0.3)

    def test_stuck_hardpoints_abort_after_two_paced_presses(self):
        result, outputs, elapsed = self.run_guard([status(True)], clear_after=3)
        self.assertEqual(result.dispatch.status, "error")
        self.assertIn("two retraction attempts", result.dispatch.reason)
        self.assertEqual(len(outputs), 2)
        self.assertGreaterEqual(elapsed, 0.6)

    def test_missing_binding_aborts_after_two_attempts_on_confirmed_deployed_state(self):
        result, outputs, _ = self.run_guard([status(True)], dispatch_ok=False)
        self.assertIn("missing binding", result.dispatch.reason)
        self.assertEqual(len(outputs), 2)

    def test_transient_unreadable_status_recovers_without_toggling(self):
        result, outputs, _ = self.run_guard([None, ValueError("partial JSON"), status(False)])
        self.assertIsNone(result)
        self.assertEqual(outputs, [])

    def test_persistently_unreadable_status_proceeds_without_toggling(self):
        result, outputs, elapsed = self.run_guard([None])
        self.assertIsNone(result)
        self.assertEqual(outputs, [])
        self.assertGreaterEqual(elapsed, 0.3)

    def test_lost_status_after_toggle_does_not_trigger_blind_second_press(self):
        result, outputs, _ = self.run_guard([status(True), None], clear_after=3)
        self.assertIsNone(result)
        self.assertEqual(len(outputs), 1)

    def test_jump_proceeds_with_warning_when_status_stays_unreadable(self):
        controls = FakeShipControls()
        clock = [0.0]
        progress = []
        def sleep(seconds): clock[0] += seconds
        result = jump(controls, FakeWatcher([
            [{"event": "StartJump", "JumpType": "Hyperspace"}],
            [{"event": "FSDJump", "StarSystem": "Sol"}],
        ]), read_status_fn=lambda: None,
                      sleeper=sleep, time_fn=lambda: clock[0],
                      hardpoints_retract_timeout_s=0.1, progress_fn=progress.append)
        self.assertEqual(result.dispatch.status, "ok")
        self.assertEqual([c["action"] for c in controls.calls], ["HyperSuperCombination", "SetSpeedZero"])
        self.assertTrue(any("Warning:" in line and "Status.json" in line for line in progress))

    def test_manual_engagement_mode_does_not_touch_hardpoints(self):
        runtime = SimpleNamespace(travel=SimpleNamespace(auto_hyperspace_engage=False))
        self.assertIsNone(engage_hyperspace_after_escape(runtime, progress_message="engage"))

    def test_transit_confirms_retraction_before_dispatching_fsd(self):
        import tempfile
        from pathlib import Path
        from tests.test_travel import _runtime
        for clears in (True, False):
            with self.subTest(clears=clears), tempfile.TemporaryDirectory() as tmp:
                journal_dir = Path(tmp)
                status_path = journal_dir / "Status.json"
                status_path.write_text('{"Flags": 64}', encoding="utf-8")
                controls = FakeShipControls()
                def toggle():
                    controls.calls.append({"action": "DeployHardpointToggle"})
                    if clears:
                        status_path.write_text('{"Flags": 0}', encoding="utf-8")
                    return ActionDispatchResult(action="DeployHardpointToggle", status="ok")
                controls.deploy_hardpoint_toggle = toggle
                jump_result = controls.hyper_super_combination
                def hyper_super_combination():
                    status_path.write_text('{"Flags": 131072}', encoding="utf-8")
                    return jump_result()
                controls.hyper_super_combination = hyper_super_combination
                runtime = _runtime(journal_dir, controls=controls)
                result = engage_hyperspace_after_escape(runtime, progress_message="engage")
                actions = [c["action"] for c in controls.calls]
                if clears:
                    self.assertIsNone(result)
                    self.assertEqual(actions, ["DeployHardpointToggle", "HyperSuperCombination"])
                else:
                    self.assertEqual(result.action, "RetractHardpoints")
                    self.assertEqual(actions, ["DeployHardpointToggle"] * 2)

    def test_pre_jump_status_reader_requires_real_flags(self):
        import tempfile
        from pathlib import Path
        from edap.status import read_status
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            for text in ('{}', '{"Flags": null}', '{"Flags": "0"}', '[]'):
                with self.subTest(text=text):
                    (path / "Status.json").write_text(text, encoding="utf-8")
                    self.assertIsNone(read_status(path, require_flags=True))

    def test_hardpoint_dispatch_uses_the_configured_semantic_binding(self):
        from edap.binding_lookup import build_binding_lookup
        from edap.bindings import Binding
        from edap.progress_controls import ProgressShipControls
        from tests.test_ship_controls import FakeInputController, _build_controls
        lookup = build_binding_lookup(
            bindings={"DeployHardpointToggle": Binding(key="K")},
            actions=["DeployHardpointToggle"],
        )
        inputs = FakeInputController()
        controls = ProgressShipControls(_build_controls(lookup, inputs), lambda _: None)
        self.assertEqual(controls.deploy_hardpoint_toggle().status, "ok")
        self.assertEqual([call["key"] for call in inputs.calls], ["k"])

    def test_timeout_config_is_loaded_and_rejects_unbounded_values(self):
        import tempfile
        from pathlib import Path
        from edap.config import ConfigError, load_config
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text('[controls.hardpoints]\nretract_timeout_seconds = 2.5\n', encoding="utf-8")
            self.assertEqual(load_config(path).controls.hardpoints_retract_timeout_seconds, 2.5)
            for value in ('0', '-1', 'inf', 'nan'):
                with self.subTest(value=value):
                    path.write_text(f'[controls.hardpoints]\nretract_timeout_seconds = {value}\n', encoding="utf-8")
                    with self.assertRaises(ConfigError):
                        load_config(path)

    def test_travel_aborts_before_fsd_from_dock_normal_space_and_supercruise(self):
        import tempfile
        from pathlib import Path
        from edap.routines.travel import TravelDestination, travel_to_station
        from tests.test_travel import _runtime
        for phase in ("docked", "normal_space", "supercruise"):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as tmp:
                journal_dir = Path(tmp)
                docked = "true" if phase == "docked" else "false"
                journal = f'{{"event":"Location","Docked":{docked},"StarSystem":"Sol","StationName":"Lincoln"}}\n'
                if phase == "supercruise":
                    journal += '{"event":"SupercruiseEntry","StarSystem":"Sol"}\n'
                (journal_dir / "Journal.240101000000.01.log").write_text(journal, encoding="utf-8")
                (journal_dir / "NavRoute.json").write_text('{"Route":[{"StarSystem":"Achenar"}]}', encoding="utf-8")
                (journal_dir / "Status.json").write_text('{"Flags":64}', encoding="utf-8")
                controls = FakeShipControls()
                watcher = FakeWatcher([
                    [], [{"event": "Undocked", "StationName": "Lincoln"}],
                    [{"event": "Music", "MusicTrack": "NoTrack"}],
                ])
                runtime = _runtime(journal_dir, controls=controls, watcher=watcher)
                result = travel_to_station(runtime, destination=TravelDestination(system="Achenar"))
                self.assertEqual(result.action, "RetractHardpoints")
                actions = [c["action"] for c in controls.calls]
                self.assertNotIn("HyperSuperCombination", actions)
                self.assertEqual(actions.count("DeployHardpointToggle"), 2)

    def test_jump_aborts_before_fsd_when_hardpoints_stay_deployed(self):
        controls = FakeShipControls()
        clock = [0.0]
        def sleep(seconds): clock[0] += seconds
        result = jump(controls, FakeWatcher([]), read_status_fn=lambda: status(True),
                      sleeper=sleep, time_fn=lambda: clock[0],
                      hardpoints_retract_timeout_s=0.1, progress_fn=lambda _: None)
        self.assertEqual(result.action, "RetractHardpoints")
        self.assertEqual([c["action"] for c in controls.calls], ["DeployHardpointToggle"] * 2)

    def test_normal_space_travel_warns_and_jumps_when_status_is_corrupt(self):
        import tempfile
        from pathlib import Path
        from edap.routines.travel import TravelDestination, travel_to_station
        from tests.test_travel import _runtime
        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            (journal_dir / "Journal.240101000000.01.log").write_text(
                '{"event":"Location","Docked":false,"StarSystem":"Sol"}\n', encoding="utf-8")
            (journal_dir / "NavRoute.json").write_text('{"Route":[{"StarSystem":"Achenar"}]}', encoding="utf-8")
            (journal_dir / "Status.json").write_text('{', encoding="utf-8")
            controls = FakeShipControls()
            progress = []
            runtime = _runtime(journal_dir, controls=controls, progress=progress,
                               watcher=FakeWatcher([[{"event": "FSDJump", "StarSystem": "Achenar"}]]))
            result = travel_to_station(runtime, destination=TravelDestination(system="Achenar"))
            self.assertEqual(result.dispatch.status, "ok")
            actions = [c["action"] for c in controls.calls]
            self.assertIn("HyperSuperCombination", actions)
            self.assertNotIn("DeployHardpointToggle", actions)
            self.assertTrue(any("Warning:" in line and "Status.json" in line for line in progress))
