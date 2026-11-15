"""Launch only after the docked menu is visibly confirmed by Status.json."""
import json
import unittest
from types import SimpleNamespace

from edcr.actions import ActionDispatchResult
from edcr.routines.docking import undock
from edcr.routines.callbacks import noop_announce, noop_progress
from tests.fakes import FakeShipControls, FakeWatcher


def status(focus=0, docked=True):
    return SimpleNamespace(gui_focus=focus, flags=SimpleNamespace(docked=docked))


class UndockFocusTests(unittest.TestCase):
    def run_launch(self, read, controls=None):
        controls = controls or FakeShipControls()
        sleeps = []
        result = undock(
            controls,
            FakeWatcher([[{"event": "Undocked"}, {"event": "Music", "MusicTrack": "NoTrack"}]]),
            read_status_fn=read, time_fn=lambda: 0.0, sleeper=sleeps.append,
            progress_fn=noop_progress, announce_fn=noop_announce,
        )
        return result, controls.calls, sleeps

    def test_services_exit_retries_lost_back_then_launches(self):
        states = iter([status(5), status(5), status(), status(), status()])
        result, calls, sleeps = self.run_launch(lambda: next(states))
        self.assertEqual(result.dispatch.status, "ok")
        self.assertEqual([c["action"] for c in calls],
                         ["UI_Back", "UI_Back", "HeadLookReset", "UI_Down", "UI_Select"])
        self.assertTrue(all(c["repeat"] == 1 for c in calls))
        self.assertGreaterEqual(sum(sleeps), 0.6)

    def test_services_never_closes_so_no_launch_keys_are_sent(self):
        result, calls, _ = self.run_launch(lambda: status(5))
        self.assertEqual(result.dispatch.status, "error")
        self.assertIn("GuiFocus 5", result.dispatch.reason)
        self.assertEqual([c["action"] for c in calls], ["UI_Back"] * 10)

    def test_unavailable_unknown_or_undocked_status_stops_before_navigation(self):
        for value in (None, status(None), status(docked=False)):
            with self.subTest(value=value):
                result, calls, _ = self.run_launch(lambda: value)
                self.assertEqual(result.dispatch.status, "error")
                self.assertEqual(calls, [])

    def test_changed_screen_blocks_each_launch_key(self):
        for states, prohibited in (([status(), status(5)], "UI_Down"),
                                   ([status(), status(), status(5)], "UI_Select"),
                                   ([status(), status(), status(docked=False)], "UI_Select")):
            with self.subTest(prohibited=prohibited, states=states):
                reads = iter(states)
                result, calls, _ = self.run_launch(lambda: next(reads))
                self.assertEqual(result.dispatch.status, "error")
                self.assertNotIn(prohibited, [c["action"] for c in calls])

    def test_transient_status_rewrite_recovers_without_blind_keys(self):
        for error in (OSError("busy"), json.JSONDecodeError("partial", "", 0)):
            reads = iter([error, None, status(), status(), status()])
            def read():
                value = next(reads)
                if isinstance(value, Exception):
                    raise value
                return value
            result, calls, sleeps = self.run_launch(read)
            self.assertEqual(result.dispatch.status, "ok")
            self.assertEqual(sleeps[:2], [0.1, 0.1])
            self.assertEqual(calls[-1]["action"], "UI_Select")

    def test_failed_back_stops_without_launch(self):
        controls = FakeShipControls()
        controls.ui_back = lambda: ActionDispatchResult(action="UI_Back", status="error", reason="input failed")
        result, calls, _ = self.run_launch(lambda: status(5), controls)
        self.assertEqual(result.dispatch.reason, "input failed")
        self.assertEqual(calls, [])
