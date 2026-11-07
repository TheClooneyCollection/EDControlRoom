from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from xml.etree.ElementTree import parse


REQUIRED_BINDINGS = [
    "YawLeftButton",
    "YawRightButton",
    "RollLeftButton",
    "RollRightButton",
    "PitchUpButton",
    "PitchDownButton",
    "SetSpeedZero",
    "SetSpeed100",
    "HyperSuperCombination",
    "DeployHardpointToggle",
    "UIFocus",
    "UI_Up",
    "UI_Down",
    "UI_Left",
    "UI_Right",
    "UI_Select",
    "UI_Back",
    "CycleNextPanel",
    "HeadLookReset",
    "PrimaryFire",
    "SecondaryFire",
    "MouseReset",
]

AUTOPILOT_REQUIRED_BINDINGS = [
    "YawLeftButton",
    "YawRightButton",
    "RollLeftButton",
    "RollRightButton",
    "PitchUpButton",
    "PitchDownButton",
    "SetSpeedZero",
    "SetSpeed100",
    "HyperSuperCombination",
    "DeployHardpointToggle",
    "UIFocus",
    "UI_Up",
    "UI_Down",
    "UI_Left",
    "UI_Right",
    "UI_Select",
    "UI_Back",
    "CycleNextPanel",
    "HeadLookReset",
]

AUTOPILOT_OPTIONAL_BINDINGS = [
    "PrimaryFire",
    "SecondaryFire",
    "MouseReset",
]


MODIFIER_ALIASES = {
    "Key_LeftShift": "LeftShift",
    "Key_RightShift": "RightShift",
    "Key_LeftAlt": "LeftAlt",
    "Key_RightAlt": "RightAlt",
    "Key_LeftControl": "LeftControl",
    "Key_RightControl": "RightControl",
}


@dataclass(frozen=True)
class Binding:
    key: str
    modifier: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)


def normalize_binding_token(token: str | None) -> str | None:
    if token is None:
        return None
    if token in MODIFIER_ALIASES:
        return MODIFIER_ALIASES[token]
    if token.startswith("Key_"):
        return token[4:]
    return token


def read_bindings(bindings_file: Path, keys_to_obtain: list[str] | None = None) -> tuple[dict[str, Binding], list[str]]:
    wanted = keys_to_obtain or REQUIRED_BINDINGS
    bindings_tree = parse(bindings_file)
    bindings_root = bindings_tree.getroot()

    resolved: dict[str, Binding] = {}
    missing: list[str] = []

    for item in bindings_root:
        if item.tag not in wanted:
            continue

        key: str | None = None
        modifier: str | None = None

        primary = item[0] if len(item) > 0 else None
        secondary = item[1] if len(item) > 1 else None

        if primary is not None and primary.attrib.get("Device", "").strip() == "Keyboard":
            key = normalize_binding_token(primary.attrib.get("Key"))
            if len(primary) > 0:
                modifier = normalize_binding_token(primary[0].attrib.get("Key"))

        if secondary is not None and secondary.attrib.get("Device", "").strip() == "Keyboard":
            key = normalize_binding_token(secondary.attrib.get("Key"))
            if len(secondary) > 0:
                modifier = normalize_binding_token(secondary[0].attrib.get("Key"))

        if key is None:
            missing.append(item.tag)
            continue

        resolved[item.tag] = Binding(key=key, modifier=modifier)

    missing.extend(sorted(set(wanted) - set(resolved.keys()) - set(missing)))
    return resolved, missing
