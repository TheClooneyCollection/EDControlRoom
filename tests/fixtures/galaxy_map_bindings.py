"""Keyboard/VKB cursor setup which also binds WASD to galaxy-map translation."""
from xml.etree.ElementTree import Element, SubElement

from edcr.bindings import REQUIRED_BINDINGS


def galaxy_map_bindings(*, arrow_secondaries: bool = False) -> Element:
    root = Element("Root")
    for action in REQUIRED_BINDINGS:
        item = SubElement(root, action)
        SubElement(item, "Primary", Device="Keyboard", Key="Key_X")
        SubElement(item, "Secondary", Device="{NoDevice}", Key="")
    for direction, key, arrow, camera, button in (
        ("Up", "W", "UpArrow", "Forward", "6"),
        ("Down", "S", "DownArrow", "Backward", "8"),
        ("Left", "A", "LeftArrow", "Left", "9"),
        ("Right", "D", "RightArrow", "Right", "7"),
    ):
        item = root.find("UI_" + direction)
        item[0].set("Key", "Key_" + key)
        item[1].attrib.update(
            Device="Keyboard" if arrow_secondaries else "231D0200",
            Key="Key_" + arrow if arrow_secondaries else "Joy_" + button,
        )
        camera_item = SubElement(root, "CamTranslate" + camera)
        SubElement(camera_item, "Primary", Device="Keyboard", Key="Key_" + key)
        SubElement(camera_item, "Secondary", Device="{NoDevice}", Key="")
    return root
