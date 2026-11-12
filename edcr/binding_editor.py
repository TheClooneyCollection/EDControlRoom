from __future__ import annotations

import shutil
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


INTERNAL_KEY_TO_XML: dict[str, str] = {
    "space": "Space",
    ",": "Comma",
    ".": "Period",
    "/": "Slash",
    "\\": "Backslash",
    ";": "Semicolon",
    "'": "Quote",
    "-": "Minus",
    "=": "Equals",
    "[": "LeftBracket",
    "]": "RightBracket",
    "enter": "Enter",
    "return": "Enter",
    "tab": "Tab",
    "escape": "Escape",
    "esc": "Escape",
    "backspace": "Backspace",
    "delete": "Delete",
    "insert": "Insert",
    "home": "Home",
    "end": "End",
    "page_up": "PageUp",
    "page_down": "PageDown",
    "up": "UpArrow",
    "down": "DownArrow",
    "left": "LeftArrow",
    "right": "RightArrow",
    "left_shift": "LeftShift",
    "right_shift": "RightShift",
    "left_alt": "LeftAlt",
    "right_alt": "RightAlt",
    "left_control": "LeftControl",
    "right_control": "RightControl",
}


MODIFIER_ALIASES_TO_CANONICAL: dict[str, str] = {
    "shift": "left_shift",
    "ctrl": "left_control",
    "control": "left_control",
    "alt": "left_alt",
    "option": "left_alt",
    "command": "left_command",
    "cmd": "left_command",
}


CANONICAL_MODIFIERS_TO_XML: dict[str, str] = {
    "left_shift": "LeftShift",
    "right_shift": "RightShift",
    "left_alt": "LeftAlt",
    "right_alt": "RightAlt",
    "left_control": "LeftControl",
    "right_control": "RightControl",
}


VALID_SLOTS = ("Primary", "Secondary")


def to_xml_key_token(internal_key: str) -> str:
    normalized = internal_key.lower().strip()
    if not normalized:
        raise ValueError("key must not be empty")
    if normalized in INTERNAL_KEY_TO_XML:
        return f"Key_{INTERNAL_KEY_TO_XML[normalized]}"
    if len(normalized) == 1 and normalized.isalnum():
        return f"Key_{normalized.upper()}"
    if normalized.startswith("numpad_") and normalized[7:].isdigit():
        return f"Key_NumPad{normalized[7:]}"
    if normalized.startswith("f") and normalized[1:].isdigit():
        return f"Key_F{normalized[1:]}"
    raise ValueError(f"cannot map key to XML token: {internal_key!r}")


def to_xml_modifier_token(internal_modifier: str) -> str:
    normalized = internal_modifier.lower().strip()
    canonical = MODIFIER_ALIASES_TO_CANONICAL.get(normalized, normalized)
    if canonical not in CANONICAL_MODIFIERS_TO_XML:
        raise ValueError(f"unsupported modifier: {internal_modifier!r}")
    return f"Key_{CANONICAL_MODIFIERS_TO_XML[canonical]}"


@dataclass(frozen=True)
class SlotChange:
    action: str
    slot: str
    key: str | None
    modifier: str | None = None


def parse_bindings_tree(path: Path) -> ET.ElementTree:
    return ET.parse(path)


def describe_binding(tree: ET.ElementTree, action: str) -> dict[str, object]:
    root = tree.getroot()
    action_el = root.find(action)
    if action_el is None:
        return {"action": action, "found": False}

    payload: dict[str, object] = {"action": action, "found": True}
    for slot in VALID_SLOTS:
        slot_el = action_el.find(slot)
        if slot_el is None:
            payload[slot] = None
            continue
        slot_payload: dict[str, object] = {
            "device": slot_el.attrib.get("Device", ""),
            "key": slot_el.attrib.get("Key", ""),
        }
        modifier_el = slot_el.find("Modifier")
        if modifier_el is not None:
            slot_payload["modifier"] = {
                "device": modifier_el.attrib.get("Device", ""),
                "key": modifier_el.attrib.get("Key", ""),
            }
        payload[slot] = slot_payload
    return payload


def apply_slot_change(tree: ET.ElementTree, change: SlotChange) -> dict[str, object]:
    if change.slot not in VALID_SLOTS:
        raise ValueError(f"slot must be Primary or Secondary, got {change.slot!r}")

    root = tree.getroot()
    action_el = root.find(change.action)
    if action_el is None:
        raise ValueError(f"action not found in bindings file: {change.action!r}")

    before = describe_binding(tree, change.action)

    slot_el = action_el.find(change.slot)
    if slot_el is None:
        slot_el = ET.SubElement(action_el, change.slot)

    for child in list(slot_el):
        slot_el.remove(child)

    if change.key is None:
        slot_el.set("Device", "{NoDevice}")
        slot_el.set("Key", "")
    else:
        slot_el.set("Device", "Keyboard")
        slot_el.set("Key", to_xml_key_token(change.key))
        if change.modifier is not None:
            modifier_el = ET.SubElement(slot_el, "Modifier")
            modifier_el.set("Device", "Keyboard")
            modifier_el.set("Key", to_xml_modifier_token(change.modifier))

    return {"before": before, "after": describe_binding(tree, change.action)}


def write_bindings(tree: ET.ElementTree, path: Path, *, backup: bool = True) -> Path | None:
    backup_path: Path | None = None
    if backup and path.exists():
        backup_path = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, backup_path)
    ET.indent(tree, space="\t", level=0)
    tree.write(path, encoding="utf-8", xml_declaration=True, short_empty_elements=True)
    return backup_path
