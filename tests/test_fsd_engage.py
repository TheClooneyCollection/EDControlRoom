import tempfile
import unittest
from pathlib import Path

from edcr.routines.transit import engage_fsd_and_confirm_charging
from edcr.tts import AnnouncementId
from tests.fakes import FakeShipControls
from tests.test_travel import _runtime

FSD_CHARGING = 1 << 17
MASS_LOCKED = 1 << 16


class FsdEngageTests(unittest.TestCase):
    def engage(self, *, flags_after_press: int | None, supercruise_fallback: bool):
        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            status_path = journal_dir / "Status.json"
            status_path.write_text('{"Flags": 0}', encoding="utf-8")
            controls = FakeShipControls()
            jump_result = controls.hyper_super_combination

            def hyper_super_combination():
                if flags_after_press is None:
                    status_path.unlink()
                else:
                    status_path.write_text(f'{{"Flags": {flags_after_press}}}', encoding="utf-8")
                return jump_result()

            controls.hyper_super_combination = hyper_super_combination
            announcements = []
            progress = []
            runtime = _runtime(journal_dir, controls=controls, announcements=announcements, progress=progress)
            engage_fsd_and_confirm_charging(runtime, supercruise_fallback=supercruise_fallback)
            actions = [call["action"] for call in controls.calls]
            return actions, [message_id for message_id, _ in announcements], progress

    def test_ready_to_jump_is_announced_only_after_the_fsd_charges(self):
        actions, announced, _ = self.engage(flags_after_press=FSD_CHARGING, supercruise_fallback=True)
        self.assertEqual(actions, ["HyperSuperCombination"])
        self.assertEqual(announced, [AnnouncementId.FSD_ENGAGE_TRYING, AnnouncementId.STATION_CLEARED])

    def test_obscured_jump_in_normal_space_falls_back_to_supercruise_and_warns(self):
        actions, announced, _ = self.engage(flags_after_press=0, supercruise_fallback=True)
        self.assertEqual(actions, ["HyperSuperCombination", "Supercruise"])
        self.assertEqual(
            announced,
            [AnnouncementId.FSD_ENGAGE_TRYING, AnnouncementId.SUPERCRUISE_FALLBACK, AnnouncementId.SUPERCRUISE_COUNTDOWN],
        )

    def test_still_mass_locked_boosts_and_retries_before_the_supercruise_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal_dir = Path(tmp)
            status_path = journal_dir / "Status.json"
            status_path.write_text(f'{{"Flags": {MASS_LOCKED}}}', encoding="utf-8")
            controls = FakeShipControls()
            jump_result = controls.hyper_super_combination
            boost_result = controls.boost
            presses = [0]

            def hyper_super_combination():
                presses[0] += 1
                if presses[0] == 2:
                    status_path.write_text(f'{{"Flags": {FSD_CHARGING}}}', encoding="utf-8")
                return jump_result()

            def boost():
                status_path.write_text('{"Flags": 0}', encoding="utf-8")
                return boost_result()

            controls.hyper_super_combination = hyper_super_combination
            controls.boost = boost
            announcements = []
            runtime = _runtime(journal_dir, controls=controls, announcements=announcements)
            engage_fsd_and_confirm_charging(runtime, supercruise_fallback=True)
        actions = [call["action"] for call in controls.calls]
        self.assertEqual(actions, ["HyperSuperCombination", "SetSpeed100", "UseBoostJuice", "HyperSuperCombination"])
        self.assertEqual(
            [message_id for message_id, _ in announcements],
            [AnnouncementId.FSD_ENGAGE_TRYING, AnnouncementId.STATION_CLEARED],
        )

    def test_obscured_jump_in_supercruise_only_warns_so_the_ship_does_not_drop_out(self):
        actions, announced, _ = self.engage(flags_after_press=0, supercruise_fallback=False)
        self.assertEqual(actions, ["HyperSuperCombination"])
        self.assertEqual(announced, [AnnouncementId.FSD_ENGAGE_TRYING, AnnouncementId.FSD_JUMP_BLOCKED])

    def test_unreadable_status_neither_claims_ready_nor_presses_supercruise(self):
        actions, announced, progress = self.engage(flags_after_press=None, supercruise_fallback=True)
        self.assertEqual(actions, ["HyperSuperCombination"])
        self.assertEqual(announced, [AnnouncementId.FSD_ENGAGE_TRYING])
        self.assertTrue(any("Status.json" in line for line in progress))


if __name__ == "__main__":
    unittest.main()
