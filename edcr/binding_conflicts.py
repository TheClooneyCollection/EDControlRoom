"""Advisory conflicts between menu cursor keys and galaxy-map camera buttons."""
from __future__ import annotations

from pathlib import Path
from xml.etree.ElementTree import Element, ParseError, parse

from edcr.binding_lookup import BindingLookup, NormalizedBinding, normalize_action_binding
from edcr.bindings import Binding

_UI_DIRECTIONS = ("UI_Up", "UI_Down", "UI_Left", "UI_Right")
_CAMERA_PREFIXES = ("CamTranslate", "CamYaw", "CamPitch", "CamZoom")


def galaxy_map_binding_conflicts(root: Element, lookup: BindingLookup) -> list[str]:
    """Compare resolved UI chords with both keyboard slots of camera buttons."""
    camera_bindings: dict[NormalizedBinding, list[str]] = {}
    for action in root:
        if not action.tag.startswith(_CAMERA_PREFIXES) or "Axis" in action.tag:
            continue
        for slot in action:
            if slot.tag not in {"Primary", "Secondary"} or slot.get("Device", "").strip() != "Keyboard":
                continue
            key = slot.get("Key")
            if not key:
                continue
            modifier = slot[0].get("Key") if len(slot) else None
            try:
                binding = normalize_action_binding(Binding(key=key, modifier=modifier))
            except ValueError:
                continue
            matches = camera_bindings.setdefault(binding, [])
            if action.tag not in matches:
                matches.append(action.tag)

    warnings: list[str] = []
    for action in _UI_DIRECTIONS:
        binding = lookup.get(action)
        if binding is None:
            continue
        conflicts = camera_bindings.get(binding, [])
        if not conflicts:
            continue
        chord = "+".join(token.replace("_", " ").upper() for token in (binding.modifier, binding.key) if token)
        warnings.append(
            f"{action} uses {chord}, which also controls the galaxy map camera "
            f"({', '.join(conflicts)}); bind an arrow key to {action} in Options > Controls > UI Mode."
        )
    return warnings


def read_galaxy_map_binding_conflicts(bindings_file: Path, lookup: BindingLookup) -> list[str]:
    """A missing or changing file must not turn an advisory check into a failure."""
    try:
        root = parse(bindings_file).getroot()
    except (OSError, ParseError):
        return []
    return galaxy_map_binding_conflicts(root, lookup)
