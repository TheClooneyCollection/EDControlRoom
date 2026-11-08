"""Keyboard keys a controller preset needs so routines can drive Elite (Steam Deck)."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass

from edap.binding_editor import VALID_SLOTS, SlotChange


@dataclass(frozen=True)
class DeckKey:
    action: str
    key: str
    modifier: str | None = None
    # Existing keyboard keys this entry replaces instead of keeping.
    replaces: tuple[str, ...] = ()


_WASD = ("Key_W", "Key_A", "Key_S", "Key_D")

# Elite's KeyboardMouseOnly defaults where it has one. Menu directions use its
# arrow-key secondaries because WASD also moves the galaxy map camera. Actions
# without a keyboard default take keys that preset leaves free.
DECK_KEYMAP: tuple[DeckKey, ...] = (
    DeckKey("YawLeftButton", "a"),
    DeckKey("YawRightButton", "d"),
    DeckKey("RollLeftButton", ","),
    DeckKey("RollRightButton", "."),
    DeckKey("PitchUpButton", "i"),
    DeckKey("PitchDownButton", "k"),
    DeckKey("SetSpeedZero", "x"),
    DeckKey("SetSpeed100", "f5"),
    DeckKey("HyperSuperCombination", "j"),
    DeckKey("DeployHardpointToggle", "u"),
    DeckKey("UseBoostJuice", "tab"),
    DeckKey("UIFocus", "left_shift"),
    DeckKey("FocusLeftPanel", "1"),
    DeckKey("CycleNextPanel", "e"),
    DeckKey("CyclePreviousPanel", "q"),
    DeckKey("UI_Up", "up", replaces=_WASD),
    DeckKey("UI_Down", "down", replaces=_WASD),
    DeckKey("UI_Left", "left", replaces=_WASD),
    DeckKey("UI_Right", "right", replaces=_WASD),
    DeckKey("UI_Select", "space"),
    DeckKey("UI_Back", "backspace"),
    DeckKey("HeadLookReset", "f6"),
    DeckKey("GalaxyMapOpen", "f7"),
    DeckKey("CamZoomIn", "z"),
)


@dataclass(frozen=True)
class KeymapStep:
    action: str
    status: str  # "add", "replace", "keep", "no_slot", "missing_action"
    detail: str
    change: SlotChange | None = None


def plan_deck_keymap(root: ET.Element, keymap: tuple[DeckKey, ...] = DECK_KEYMAP) -> list[KeymapStep]:
    """Fill keyboard keys without touching controller bindings or keys the user chose."""
    steps: list[KeymapStep] = []
    for entry in keymap:
        action_el = root.find(entry.action)
        if action_el is None:
            steps.append(KeymapStep(entry.action, "missing_action", "not in this bindings file"))
            continue
        slots = {slot: action_el.find(slot) for slot in VALID_SLOTS}
        keyboard = {
            slot: el for slot, el in slots.items() if el is not None and el.get("Device") == "Keyboard"
        }
        replaceable = [slot for slot, el in keyboard.items() if el.get("Key") in entry.replaces and len(el) == 0]
        kept = [slot for slot in keyboard if slot not in replaceable]
        wanted = _describe(entry.key, entry.modifier)
        if kept:
            existing = ", ".join(_describe_slot(keyboard[slot]) for slot in kept)
            steps.append(KeymapStep(entry.action, "keep", f"already on keyboard: {existing}"))
            continue
        if replaceable:
            slot = replaceable[0]
            steps.append(
                KeymapStep(
                    entry.action,
                    "replace",
                    f"{slot}: {_describe_slot(keyboard[slot])} -> {wanted}",
                    SlotChange(entry.action, slot, entry.key, entry.modifier),
                )
            )
            continue
        # Secondary first so the controller binding Elite put in Primary stays.
        free = [slot for slot in reversed(VALID_SLOTS) if _is_free(slots[slot])]
        if not free:
            steps.append(KeymapStep(entry.action, "no_slot", "both slots hold controller bindings"))
            continue
        steps.append(
            KeymapStep(
                entry.action,
                "add",
                f"{free[0]}: {wanted}",
                SlotChange(entry.action, free[0], entry.key, entry.modifier),
            )
        )
    return steps


def _is_free(slot_el: ET.Element | None) -> bool:
    return slot_el is None or slot_el.get("Device") in {"{NoDevice}", ""} or not slot_el.get("Key")


def _describe(key: str, modifier: str | None) -> str:
    return f"{modifier}+{key}" if modifier else key


def _describe_slot(slot_el: ET.Element) -> str:
    key = slot_el.get("Key", "").removeprefix("Key_")
    modifier = slot_el.find("Modifier")
    if modifier is not None:
        return f"{modifier.get('Key', '').removeprefix('Key_')}+{key}"
    return key
