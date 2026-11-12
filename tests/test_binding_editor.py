from __future__ import annotations

import unittest
import xml.etree.ElementTree as ET
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from edcr.binding_editor import (
    SlotChange,
    apply_slot_change,
    describe_binding,
    parse_bindings_tree,
    to_xml_key_token,
    to_xml_modifier_token,
    write_bindings,
)


SAMPLE = """<?xml version="1.0" encoding="UTF-8" ?>
<Root PresetName="Custom" MajorVersion="4" MinorVersion="2">
\t<KeyboardLayout>en-US</KeyboardLayout>
\t<PitchDownButton>
\t\t<Primary Device="Keyboard" Key="Key_Period" />
\t\t<Secondary Device="{NoDevice}" Key="" />
\t</PitchDownButton>
\t<SetSpeedZero>
\t\t<Primary Device="Keyboard" Key="Key_X">
\t\t\t<Modifier Device="Keyboard" Key="Key_LeftControl" />
\t\t</Primary>
\t\t<Secondary Device="{NoDevice}" Key="" />
\t</SetSpeedZero>
\t<MouseXMode Value="Bindings_MouseRoll" />
</Root>
"""


def _parse(xml_text: str) -> ET.ElementTree:
    return ET.ElementTree(ET.fromstring(xml_text))


class KeyTokenTests(unittest.TestCase):
    def test_letter(self) -> None:
        self.assertEqual(to_xml_key_token("a"), "Key_A")
        self.assertEqual(to_xml_key_token("X"), "Key_X")

    def test_digit(self) -> None:
        self.assertEqual(to_xml_key_token("1"), "Key_1")

    def test_punctuation(self) -> None:
        self.assertEqual(to_xml_key_token("."), "Key_Period")
        self.assertEqual(to_xml_key_token(","), "Key_Comma")
        self.assertEqual(to_xml_key_token("["), "Key_LeftBracket")
        self.assertEqual(to_xml_key_token("]"), "Key_RightBracket")

    def test_special(self) -> None:
        self.assertEqual(to_xml_key_token("space"), "Key_Space")
        self.assertEqual(to_xml_key_token("enter"), "Key_Enter")
        self.assertEqual(to_xml_key_token("backspace"), "Key_Backspace")
        self.assertEqual(to_xml_key_token("up"), "Key_UpArrow")

    def test_modifier_as_key(self) -> None:
        self.assertEqual(to_xml_key_token("left_shift"), "Key_LeftShift")

    def test_function_keys(self) -> None:
        self.assertEqual(to_xml_key_token("f1"), "Key_F1")
        self.assertEqual(to_xml_key_token("f12"), "Key_F12")

    def test_numpad(self) -> None:
        self.assertEqual(to_xml_key_token("numpad_0"), "Key_NumPad0")
        self.assertEqual(to_xml_key_token("numpad_9"), "Key_NumPad9")

    def test_unknown_key_raises(self) -> None:
        with self.assertRaises(ValueError):
            to_xml_key_token("not_a_real_key")


class ModifierTokenTests(unittest.TestCase):
    def test_canonical(self) -> None:
        self.assertEqual(to_xml_modifier_token("left_shift"), "Key_LeftShift")
        self.assertEqual(to_xml_modifier_token("right_control"), "Key_RightControl")

    def test_aliases(self) -> None:
        self.assertEqual(to_xml_modifier_token("shift"), "Key_LeftShift")
        self.assertEqual(to_xml_modifier_token("ctrl"), "Key_LeftControl")
        self.assertEqual(to_xml_modifier_token("control"), "Key_LeftControl")
        self.assertEqual(to_xml_modifier_token("alt"), "Key_LeftAlt")

    def test_unknown_modifier_raises(self) -> None:
        with self.assertRaises(ValueError):
            to_xml_modifier_token("weird")


class DescribeBindingTests(unittest.TestCase):
    def test_plain_key(self) -> None:
        tree = _parse(SAMPLE)

        description = describe_binding(tree, "PitchDownButton")

        self.assertEqual(description["action"], "PitchDownButton")
        self.assertTrue(description["found"])
        self.assertEqual(
            description["Primary"],
            {"device": "Keyboard", "key": "Key_Period"},
        )
        self.assertEqual(
            description["Secondary"],
            {"device": "{NoDevice}", "key": ""},
        )

    def test_key_with_modifier(self) -> None:
        tree = _parse(SAMPLE)

        description = describe_binding(tree, "SetSpeedZero")

        self.assertEqual(
            description["Primary"],
            {
                "device": "Keyboard",
                "key": "Key_X",
                "modifier": {"device": "Keyboard", "key": "Key_LeftControl"},
            },
        )

    def test_missing_action(self) -> None:
        tree = _parse(SAMPLE)

        description = describe_binding(tree, "ThisDoesNotExist")

        self.assertEqual(description, {"action": "ThisDoesNotExist", "found": False})


class ApplySlotChangeTests(unittest.TestCase):
    def test_set_plain_key_replaces_existing(self) -> None:
        tree = _parse(SAMPLE)

        diff = apply_slot_change(
            tree, SlotChange(action="PitchDownButton", slot="Primary", key="i")
        )

        self.assertEqual(diff["before"]["Primary"]["key"], "Key_Period")
        self.assertEqual(
            diff["after"]["Primary"],
            {"device": "Keyboard", "key": "Key_I"},
        )

    def test_set_key_with_modifier(self) -> None:
        tree = _parse(SAMPLE)

        diff = apply_slot_change(
            tree,
            SlotChange(action="PitchDownButton", slot="Primary", key=".", modifier="ctrl"),
        )

        self.assertEqual(
            diff["after"]["Primary"],
            {
                "device": "Keyboard",
                "key": "Key_Period",
                "modifier": {"device": "Keyboard", "key": "Key_LeftControl"},
            },
        )

    def test_set_clears_previous_modifier(self) -> None:
        tree = _parse(SAMPLE)

        diff = apply_slot_change(
            tree, SlotChange(action="SetSpeedZero", slot="Primary", key="x")
        )

        self.assertEqual(
            diff["after"]["Primary"],
            {"device": "Keyboard", "key": "Key_X"},
        )
        self.assertNotIn("modifier", diff["after"]["Primary"])

    def test_clear_slot(self) -> None:
        tree = _parse(SAMPLE)

        diff = apply_slot_change(
            tree, SlotChange(action="PitchDownButton", slot="Primary", key=None)
        )

        self.assertEqual(
            diff["after"]["Primary"],
            {"device": "{NoDevice}", "key": ""},
        )

    def test_unknown_action_raises(self) -> None:
        tree = _parse(SAMPLE)

        with self.assertRaises(ValueError):
            apply_slot_change(tree, SlotChange(action="Nope", slot="Primary", key="a"))

    def test_invalid_slot_raises(self) -> None:
        tree = _parse(SAMPLE)

        with self.assertRaises(ValueError):
            apply_slot_change(
                tree, SlotChange(action="PitchDownButton", slot="Tertiary", key="a")
            )


class WriteBindingsRoundTripTests(unittest.TestCase):
    def test_round_trip_preserves_other_actions_and_writes_backup(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp) / "Custom.4.2.binds"
            tmp_path.write_text(SAMPLE, encoding="utf-8")

            tree = parse_bindings_tree(tmp_path)
            apply_slot_change(
                tree, SlotChange(action="PitchDownButton", slot="Primary", key="i")
            )
            backup_path = write_bindings(tree, tmp_path)

            self.assertIsNotNone(backup_path)
            assert backup_path is not None
            self.assertEqual(backup_path.read_text(encoding="utf-8"), SAMPLE)

            reparsed = parse_bindings_tree(tmp_path)
            self.assertEqual(
                describe_binding(reparsed, "PitchDownButton")["Primary"],
                {"device": "Keyboard", "key": "Key_I"},
            )
            self.assertEqual(
                describe_binding(reparsed, "SetSpeedZero")["Primary"],
                {
                    "device": "Keyboard",
                    "key": "Key_X",
                    "modifier": {"device": "Keyboard", "key": "Key_LeftControl"},
                },
            )
            root = reparsed.getroot()
            mouse_mode = root.find("MouseXMode")
            self.assertIsNotNone(mouse_mode)
            self.assertEqual(mouse_mode.attrib.get("Value"), "Bindings_MouseRoll")

    def test_skipping_backup_does_not_write_one(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp) / "Custom.4.2.binds"
            tmp_path.write_text(SAMPLE, encoding="utf-8")

            tree = parse_bindings_tree(tmp_path)
            apply_slot_change(
                tree, SlotChange(action="PitchDownButton", slot="Primary", key="i")
            )
            backup_path = write_bindings(tree, tmp_path, backup=False)

            self.assertIsNone(backup_path)
            self.assertFalse(tmp_path.with_suffix(tmp_path.suffix + ".bak").exists())
