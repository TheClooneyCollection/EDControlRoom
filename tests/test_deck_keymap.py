from __future__ import annotations

import io
import unittest
import xml.etree.ElementTree as ET
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from edcr.binding_lookup import load_binding_lookup
from edcr.bindings import AUTOPILOT_REQUIRED_BINDINGS
from edcr.deck_keymap import DECK_KEYMAP, DeckKey, plan_deck_keymap
from edcr.ship_controls import DEFAULT_SHIP_CONTROL_ACTIONS
from tools import deck_keymap as deck_keymap_tool

_PAD = '<Primary Device="28DE11FF" Key="GamePad_FaceRight" />'
_PAD2 = '<Secondary Device="28DE11FF" Key="GamePad_FaceLeft" />'
_NONE_P = '<Primary Device="{NoDevice}" Key="" />'
_NONE_S = '<Secondary Device="{NoDevice}" Key="" />'


def _root(*actions: tuple[str, str, str]) -> ET.Element:
    body = "".join(f"<{name}>{primary}{secondary}</{name}>" for name, primary, secondary in actions)
    return ET.fromstring(f"<Root>{body}</Root>")


def _plan(entry: DeckKey, primary: str, secondary: str) -> tuple[str, str | None]:
    (step,) = plan_deck_keymap(_root((entry.action, primary, secondary)), (entry,))
    return step.status, step.change.slot if step.change else None


class DeckKeymapPlanTests(unittest.TestCase):
    def test_where_each_key_goes(self) -> None:
        boost = DeckKey("UseBoostJuice", "tab")
        up = DeckKey("UI_Up", "up", replaces=("Key_W",))
        cases = [
            # controller in Primary, Secondary free: key goes to Secondary
            (boost, _PAD, _NONE_S, ("add", "Secondary")),
            # nothing bound: Secondary first, Primary stays free for the pad
            (boost, _NONE_P, _NONE_S, ("add", "Secondary")),
            # controller in Secondary only: Primary takes the key
            (boost, _NONE_P, _PAD2, ("add", "Primary")),
            # a key the user picked stays
            (boost, _PAD, '<Secondary Device="Keyboard" Key="Key_B" />', ("keep", None)),
            # both slots on the controller: nothing to write
            (boost, _PAD, _PAD2, ("no_slot", None)),
            # WASD menu keys fight the galaxy map camera, so they get replaced
            (up, _PAD, '<Secondary Device="Keyboard" Key="Key_W" />', ("replace", "Secondary")),
            # a WASD chord with a modifier is a deliberate choice and stays
            (
                up,
                _PAD,
                '<Secondary Device="Keyboard" Key="Key_W"><Modifier Device="Keyboard" Key="Key_LeftAlt" /></Secondary>',
                ("keep", None),
            ),
        ]
        for entry, primary, secondary, expected in cases:
            with self.subTest(entry=entry.action, primary=primary, secondary=secondary):
                self.assertEqual(_plan(entry, primary, secondary), expected)

    def test_an_action_missing_from_the_file_is_reported_not_written(self) -> None:
        (step,) = plan_deck_keymap(_root(), (DeckKey("UseBoostJuice", "tab"),))

        self.assertEqual((step.status, step.change), ("missing_action", None))

    def test_keymap_covers_every_action_routines_press_and_has_no_duplicate_keys(self) -> None:
        actions = {entry.action for entry in DECK_KEYMAP}
        self.assertLessEqual(set(AUTOPILOT_REQUIRED_BINDINGS), actions)
        self.assertLessEqual(set(DEFAULT_SHIP_CONTROL_ACTIONS), actions)
        chords = [(entry.key, entry.modifier) for entry in DECK_KEYMAP]
        self.assertEqual(len(chords), len(set(chords)))


class DeckKeymapToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.path = Path(self.tmpdir.name) / "Custom.4.2.binds"
        actions = [(entry.action, _PAD, _NONE_S) for entry in DECK_KEYMAP]
        body = "".join(f"<{name}>{primary}{secondary}</{name}>" for name, primary, secondary in actions)
        self.original = f'<?xml version="1.0" encoding="UTF-8" ?>\n<Root PresetName="Custom">{body}</Root>\n'
        self.path.write_text(self.original, encoding="utf-8")

    def _run(self, *args: str) -> str:
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(deck_keymap_tool.main(["--bindings-file", str(self.path), *args]), 0)
        return out.getvalue()

    def test_without_write_only_shows_the_plan(self) -> None:
        output = self._run()

        self.assertIn("UseBoostJuice", output)
        self.assertIn("rerun with --write", output)
        self.assertEqual(self.path.read_text(encoding="utf-8"), self.original)

    def test_write_binds_every_routine_action_keeps_the_pad_and_the_first_backup(self) -> None:
        self._run("--write")
        output = self._run("--write")

        lookup = load_binding_lookup(self.path, actions=[entry.action for entry in DECK_KEYMAP])
        self.assertEqual(lookup.issues(), {})
        self.assertEqual(lookup.get("UseBoostJuice").key, "tab")
        self.assertIn('Key="GamePad_FaceRight"', self.path.read_text(encoding="utf-8"))
        self.assertEqual((self.path.parent / "Custom.4.2.binds.bak").read_text(encoding="utf-8"), self.original)
        self.assertIn("Nothing to change.", output)


if __name__ == "__main__":
    unittest.main()
