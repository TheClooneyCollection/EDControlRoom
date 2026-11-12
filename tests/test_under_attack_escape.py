from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from edcr.actions import ActionDispatchResult
from edcr.routines.callbacks import noop_announce, noop_progress
from edcr.routines.docking import UNDER_ATTACK_FLEE_AFTER_UNDOCK_S, _wait_for_clear_of_station, dock, undock
from edcr.routines.transit import undock_and_route_to_system
from edcr.tts import AnnouncementId
from tests.fakes import FakeShipControls, FakeWatcher
from tests.test_travel import _runtime, _ticking_clock

_UNDOCKED = {"event": "Undocked", "StationName": "Voltaire Terminal", "StationType": "Dodec"}
_UNDER_ATTACK = {"event": "UnderAttack", "Target": "You"}
_SHIELDS_DOWN = {"event": "ShieldState", "ShieldsUp": False}
_HULL_DAMAGE = {"event": "HullDamage", "Health": 0.8, "PlayerPilot": True, "Fighter": False}
_NO_FIRE_ZONE_EXITED = {"event": "ReceiveText", "Message": "$STATION_NoFireZone_exited;", "Channel": "npc"}


def _wait(batches, *, time_fn, threats: list[dict[str, object]]):
    return _wait_for_clear_of_station(
        FakeWatcher(batches),
        undocked_event=_UNDOCKED,
        undocked_at=0.0,
        threat_fn=threats.append,
        no_track_timeout_s=600.0,
        time_fn=time_fn,
        progress_fn=noop_progress,
    )


class ClearOfStationThreatTests(unittest.TestCase):
    def test_damage_escapes_immediately_and_reports_threat_once(self) -> None:
        for damage in (_SHIELDS_DOWN, _HULL_DAMAGE):
            with self.subTest(damage=damage["event"]):
                threats: list[dict[str, object]] = []
                result = _wait(
                    [[{"event": "Music", "MusicTrack": "Combat_Dogfight"}, _UNDER_ATTACK, _UNDER_ATTACK], [damage]],
                    time_fn=lambda: 1.0,
                    threats=threats,
                )

                self.assertEqual(result.action, "UnderAttack")
                self.assertEqual(result.trigger_event, damage)
                self.assertEqual(threats, [_UNDER_ATTACK])

    def test_attack_without_damage_waits_for_launch_to_leave_the_slot(self) -> None:
        clock = _ticking_clock()
        threats: list[dict[str, object]] = []

        result = _wait([[_UNDER_ATTACK]], time_fn=clock, threats=threats)

        self.assertEqual(result.action, "UnderAttack")
        self.assertEqual(result.trigger_event, _UNDER_ATTACK)
        self.assertGreaterEqual(clock(), UNDER_ATTACK_FLEE_AFTER_UNDOCK_S)
        self.assertEqual(threats, [_UNDER_ATTACK])

    def test_station_clear_cue_while_under_attack_still_escapes(self) -> None:
        for cue in (_NO_FIRE_ZONE_EXITED, {"event": "Music", "MusicTrack": "NoTrack"}):
            with self.subTest(cue=cue["event"]):
                result = _wait([[_UNDER_ATTACK], [cue]], time_fn=lambda: 1.0, threats=[])

                self.assertEqual(result.action, "UnderAttack")

    def test_attacks_on_other_ships_are_ignored(self) -> None:
        threats: list[dict[str, object]] = []

        result = _wait(
            [[{"event": "UnderAttack", "Target": "Fighter"}], [_NO_FIRE_ZONE_EXITED]],
            time_fn=lambda: 1.0,
            threats=threats,
        )

        self.assertEqual(result.action, "NoFireZoneExited")
        self.assertEqual(threats, [])


class StandaloneUndockThreatTests(unittest.TestCase):
    def test_undock_announces_and_stops_for_manual_control(self) -> None:
        announcements: list[object] = []

        result = undock(
            FakeShipControls(),
            FakeWatcher([[], [_UNDOCKED], [_UNDER_ATTACK, _SHIELDS_DOWN]]),
            undock_timeout_s=10.0,
            no_track_timeout_s=10.0,
            step_delay_s=0.0,
            time_fn=_ticking_clock(),
            sleeper=lambda _: None,
            progress_fn=noop_progress,
            announce_fn=lambda message_id, **_: announcements.append(message_id),
        )

        self.assertEqual(result.dispatch.status, "error")
        self.assertEqual(result.action, "UnderAttack")
        self.assertEqual(announcements, [AnnouncementId.UNDER_ATTACK])


class DockingThreatTests(unittest.TestCase):
    def test_attack_while_docking_warns_once_and_keeps_docking(self) -> None:
        announcements: list[object] = []
        controls = FakeShipControls()

        result = dock(
            controls,
            FakeWatcher([
                [],
                [{"event": "DockingGranted", "LandingPad": 9}],
                [{"event": "Music", "MusicTrack": "Combat_Dogfight"}, _UNDER_ATTACK, _UNDER_ATTACK],
                [_SHIELDS_DOWN],
                [{"event": "Docked", "StationName": "Voltaire Terminal"}],
            ]),
            wait_for_supercruise_exit=False,
            max_retries=1,
            request_timeout_s=10.0,
            dock_timeout_s=60.0,
            step_delay_s=0.0,
            time_fn=lambda: 1.0,
            sleeper=lambda _: None,
            progress_fn=noop_progress,
            announce_fn=lambda message_id, **_: announcements.append(message_id),
        )

        self.assertEqual(result.dispatch.status, "ok")
        self.assertEqual(result.trigger_event, {"event": "Docked", "StationName": "Voltaire Terminal"})
        self.assertEqual(
            announcements,
            [AnnouncementId.AUTO_DOCKING_ENGAGED, AnnouncementId.UNDER_ATTACK],
        )
        self.assertNotIn("UseBoostJuice", [call["action"] for call in controls.calls])


class SupercruiseEscapeTests(unittest.TestCase):
    def _undock_under_attack(self, *, controls: FakeShipControls, escape_batches):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        announcements: list[tuple[AnnouncementId, dict[str, object]]] = []
        runtime = _runtime(
            Path(tmp.name),
            controls=controls,
            watcher=FakeWatcher([[], [_UNDOCKED], [_UNDER_ATTACK, _SHIELDS_DOWN], *escape_batches]),
            announcements=announcements,
        )
        result = undock_and_route_to_system(
            runtime,
            current_label="Voltaire Terminal",
            current_system="Pegasi Sector KD-R b5-0",
            destination_system="Pegasi Sector KD-R b5-0",
            routine_name="haul",
        )
        actions = [call["action"] for call in controls.calls]
        return result, actions, [message_id for message_id, _ in announcements]

    def test_escapes_into_supercruise_and_asks_player_to_align_and_jump(self) -> None:
        controls = FakeShipControls()

        result, actions, announcements = self._undock_under_attack(
            controls=controls,
            escape_batches=[[{"event": "StartJump", "JumpType": "Supercruise"}], [{"event": "SupercruiseEntry"}]],
        )

        self.assertEqual(result.dispatch.status, "ok")
        self.assertEqual(result.action, "SupercruiseEscape")
        self.assertEqual(result.trigger_event, {"event": "SupercruiseEntry"})
        self.assertIn("Supercruise", actions)
        self.assertNotIn("HyperSuperCombination", actions)
        self.assertLess(actions.index("SetSpeed100"), actions.index("Supercruise"))
        self.assertEqual(
            announcements,
            [AnnouncementId.UNDER_ATTACK, AnnouncementId.SUPERCRUISE_ESCAPE_ALIGN],
        )

    def test_falls_back_to_fsd_toggle_when_supercruise_is_unbound(self) -> None:
        controls = FakeShipControls(
            supercruise_result=ActionDispatchResult(action="Supercruise", status="missing_binding"),
        )

        result, actions, announcements = self._undock_under_attack(
            controls=controls,
            escape_batches=[[{"event": "StartJump", "JumpType": "Hyperspace"}]],
        )

        self.assertEqual(result.dispatch.status, "ok")
        self.assertEqual(actions[-2:], ["Supercruise", "HyperSuperCombination"])
        self.assertEqual(announcements[-1], AnnouncementId.SUPERCRUISE_ESCAPE_ALIGN)

    def test_aborts_when_fsd_never_engages(self) -> None:
        result, _, announcements = self._undock_under_attack(controls=FakeShipControls(), escape_batches=[])

        self.assertEqual(result.dispatch.status, "error")
        self.assertEqual(result.action, "SupercruiseEscape")
        self.assertEqual(announcements, [AnnouncementId.UNDER_ATTACK, AnnouncementId.HAUL_ABORTED])


if __name__ == "__main__":
    unittest.main()
