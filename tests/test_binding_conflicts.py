from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from xml.etree.ElementTree import ElementTree, SubElement

from edap.binding_conflicts import galaxy_map_binding_conflicts, read_galaxy_map_binding_conflicts
from edap.binding_lookup import load_binding_lookup
from edap.bindings import read_bindings
from edap.control_room.app import ControlRoomApp
from edap.runtime import ResolvedPath
from tests.fixtures.galaxy_map_bindings import galaxy_map_bindings
from tools.check_bindings import main


class GalaxyMapBindingConflictTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "Custom.4.2.binds"

    def load(self, root):
        ElementTree(root).write(self.path, encoding="utf-8")
        return load_binding_lookup(self.path)

    def test_wasd_cursor_with_vkb_secondaries_warns_for_all_directions_without_changing_lookup(self):
        root = galaxy_map_bindings()
        lookup = self.load(root)
        before = lookup.to_dict()
        warnings = galaxy_map_binding_conflicts(root, lookup)
        self.assertEqual(len(warnings), 4)
        for direction, key, camera in (("Up", "W", "Forward"), ("Down", "S", "Backward"), ("Left", "A", "Left"), ("Right", "D", "Right")):
            self.assertTrue(any(f"UI_{direction} uses {key}" in warning and f"CamTranslate{camera}" in warning for warning in warnings))
        self.assertEqual(lookup.to_dict(), before)

    def test_arrow_secondaries_take_priority_and_remove_conflicts(self):
        root = galaxy_map_bindings(arrow_secondaries=True)
        lookup = self.load(root)
        self.assertEqual(galaxy_map_binding_conflicts(root, lookup), [])
        self.assertEqual(lookup.get("UI_Up").key, "up")

    def test_different_camera_modifier_does_not_conflict(self):
        root = galaxy_map_bindings()
        for action in root:
            if action.tag.startswith("Cam"):
                SubElement(action[0], "Modifier", Device="Keyboard", Key="Key_LeftShift")
        self.assertEqual(galaxy_map_binding_conflicts(root, self.load(root)), [])

    def test_all_camera_button_families_and_secondary_slots_are_checked(self):
        root = galaxy_map_bindings(arrow_secondaries=True)
        for tag in ("CamTranslateForward", "CamYawLeft", "CamPitchUp", "CamZoomIn"):
            action = root.find(tag)
            if action is None:
                action = SubElement(root, tag)
            SubElement(action, "Secondary", Device="Keyboard", Key="Key_UpArrow")
        warnings = galaxy_map_binding_conflicts(root, self.load(root))
        self.assertEqual(len(warnings), 1)
        for action in ("CamTranslateForward", "CamYawLeft", "CamPitchUp", "CamZoomIn"):
            self.assertIn(action, warnings[0])

    def test_matching_modifier_chords_warn_and_aliases_are_normalized(self):
        root = galaxy_map_bindings(arrow_secondaries=True)
        up = root.find("UI_Up")
        SubElement(up[1], "Modifier", Device="Keyboard", Key="Key_LeftShift")
        camera = SubElement(root, "CamYawLeft")
        slot = SubElement(camera, "Secondary", Device="Keyboard", Key="up")
        SubElement(slot, "Modifier", Device="Keyboard", Key="LeftShift")
        warnings = galaxy_map_binding_conflicts(root, self.load(root))
        self.assertEqual(len(warnings), 1)
        self.assertIn("UI_Up uses LEFT SHIFT+UP", warnings[0])
        self.assertIn("CamYawLeft", warnings[0])

    def test_camera_axes_and_joystick_keys_are_ignored(self):
        root = galaxy_map_bindings(arrow_secondaries=True)
        axis = SubElement(root, "CamYawAxis")
        SubElement(axis, "Primary", Device="Keyboard", Key="Key_UpArrow")
        button = SubElement(root, "CamYawLeft")
        SubElement(button, "Primary", Device="231D0200", Key="Key_UpArrow")
        self.assertEqual(galaxy_map_binding_conflicts(root, self.load(root)), [])

    def test_secondary_uses_its_own_modifier_instead_of_carrying_primary_modifier(self):
        for secondary_modifier in (None, "Key_LeftControl"):
            with self.subTest(modifier=secondary_modifier):
                root = galaxy_map_bindings(arrow_secondaries=True)
                up = root.find("UI_Up")
                SubElement(up[0], "Modifier", Device="Keyboard", Key="Key_LeftShift")
                if secondary_modifier:
                    SubElement(up[1], "Modifier", Device="Keyboard", Key=secondary_modifier)
                self.load(root)
                resolved, _ = read_bindings(self.path)
                self.assertEqual(resolved["UI_Up"].modifier, "LeftControl" if secondary_modifier else None)
                self.assertEqual(resolved["UI_Up"].key, "UpArrow")

    def test_startup_logs_conflicts_even_when_all_keyboard_mappings_are_usable(self):
        lookup = self.load(galaxy_map_bindings())
        lines = []
        source = ResolvedPath(configured={"status": "ok"}, auto_detected={}, effective={"path": str(self.path)})
        app = SimpleNamespace(_ctx=SimpleNamespace(bindings=source, binding_lookup=lookup), _log=lines.append)
        ControlRoomApp._log_bindings_status(app)
        output = "\n".join(lines)
        self.assertEqual(output.count("Bindings warning"), 4)
        self.assertIn("UI_Up uses W", output)
        self.assertIn("Options > Controls > UI Mode", output)
        self.assertNotIn("no usable keyboard mapping", output)

    def test_check_tool_warns_in_text_and_json_but_still_reports_ok(self):
        self.load(galaxy_map_bindings())
        config = self.path.parent / "config.toml"
        config.write_text("[paths]\n", encoding="utf-8")
        source = ResolvedPath(configured={"status": "ok"}, auto_detected={}, effective={"path": str(self.path)})
        for json_output in (False, True):
            with self.subTest(json=json_output), redirect_stdout(io.StringIO()) as output:
                result = main(["--config", str(config)] + (["--json"] if json_output else []),
                              runtime_builder=lambda _: SimpleNamespace(bindings=source))
            self.assertEqual(result, 0)
            if json_output:
                payload = json.loads(output.getvalue())
                self.assertTrue(payload["ok"])
                self.assertEqual(payload["issue_count"], 0)
                self.assertEqual(len(payload["warnings"]), 4)
                self.assertEqual(payload["supported"]["UI_Up"]["key"], "w")
            else:
                self.assertIn("Bindings check: OK", output.getvalue())
                self.assertIn("Bindings warning: UI_Up uses W", output.getvalue())

    def test_advisory_read_failure_does_not_block_startup(self):
        lookup = self.load(galaxy_map_bindings())
        self.path.write_text("<Root>", encoding="utf-8")
        self.assertEqual(read_galaxy_map_binding_conflicts(self.path, lookup), [])
        self.path.unlink()
        self.assertEqual(read_galaxy_map_binding_conflicts(self.path, lookup), [])
