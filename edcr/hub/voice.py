"""The hub voices one node's callouts (plan 0015 step 7).

Every node speaks its own callouts and also sends each callout's text up the link (a `callout`
frame, live only). The hub's own game reaches it through its broker. The voiced node is the one last
picked in a hub page's node picker (hub-wide; empty: the hub's own game). Two switches play its
callouts on the hub too: the hub speakers (hub-wide) and each listening page (per browser). Pages that
listen get each callout as a message, with a Piper WAV when the hub has Piper, else just the text for
browser speech.

A third switch mutes the voiced node, so its callouts play only on the hub: the hub sends the node a
`voice_mute` frame and the node stops speaking its own callouts but still sends them up. The mute
holds only while the callouts play somewhere on the hub (hub speakers on for a peer, or a page
listening); otherwise, or when another node is picked, the hub unmutes the node, and a peer unmutes
itself when its link drops, so callouts are never silently lost.

Hub-wide rather than per browser, because the speakers are one device and two nodes must never talk
over each other: only one node is ever voiced, and the hub speakers queue its lines behind the hub's
own callouts. The hub's own game already speaks on the hub speakers, so it is never spoken twice.
"""
from __future__ import annotations

import base64
import itertools
import json
import threading
from pathlib import Path
from typing import Any, Callable

# The broker message carrying one callout (`edcr.control_room.server.broker`).
ANNOUNCEMENT_MESSAGE = "event.announcement_emitted"
# A node's callout up the link: {"type": "callout", "text": ...}.
CALLOUT_FRAME = "callout"
# The hub mutes or unmutes a node's own callouts: {"type": "voice_mute", "muted": bool}.
VOICE_MUTE_FRAME = "voice_mute"

# Hands one voice message to a listening page.
Listener = Callable[[dict[str, Any]], None]


def callout_text(message: dict[str, Any]) -> str | None:
    """The spoken text of a broker message, when it is a callout."""
    if message.get("message_type") != ANNOUNCEMENT_MESSAGE:
        return None
    payload = message.get("payload")
    text = str(payload.get("message_text") or "").strip() if isinstance(payload, dict) else ""
    return text or None


def node_muter(local_node_id: str, mute_local: Callable[[bool], None],
               send_to_peer: Callable[[str, dict[str, Any]], bool]) -> Callable[[str, bool], None]:
    """Mutes the hub's own game directly and a peer over its link (dropped when it is offline; the
    hub sends it again when the peer links)."""

    def set_muted(node_id: str, muted: bool) -> None:
        if node_id == local_node_id:
            mute_local(muted)
        else:
            send_to_peer(node_id, {"type": VOICE_MUTE_FRAME, "muted": muted})

    return set_muted


class HubVoice:
    """Hub-wide voice settings, the hub speakers, the pages listening and the voiced node's mute. Thread-safe.

    `speak` queues a line on the hub's own speaker (the queue its local callouts use), `synthesize`
    turns a line into WAV bytes (None: the hub has no Piper), `run_in_background` runs synthesis off
    the caller's thread and must run work in order (one worker), `names` gives a node's name and
    `set_muted` mutes or unmutes a node's own callouts (`node_muter`).
    """

    def __init__(
        self,
        *,
        local_node_id: str,
        settings_file: Path,
        speak: Callable[[str], bool],
        synthesize: Callable[[str], bytes] | None,
        names: Callable[[str], str],
        set_muted: Callable[[str, bool], None],
        run_in_background: Callable[[Callable[[], None]], None],
        log: Callable[[str], None],
    ) -> None:
        self._local_node_id = local_node_id
        self._settings_file = settings_file
        self._speak = speak
        self._synthesize = synthesize
        self._names = names
        self._set_muted = set_muted
        self._run_in_background = run_in_background
        self._log = log
        # Reentrant: mutes go out under it, so they reach nodes in the order the settings changed.
        self._lock = threading.RLock()
        self._node_id, self._speakers, self._mute = self._load()
        self._listeners: dict[int, Listener] = {}
        self._ids = itertools.count(1)
        # The node muted now, if any.
        self._muted_node = ""

    def _load(self) -> tuple[str, bool, bool]:
        try:
            saved = json.loads(self._settings_file.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return "", False, False
        except (OSError, ValueError) as exc:
            self._log(f"Hub voice settings {self._settings_file} unreadable, voice off: {exc}")
            return "", False, False
        if not isinstance(saved, dict):
            return "", False, False
        node_id = saved.get("node_id")
        return (node_id.strip() if isinstance(node_id, str) else ""), saved.get("speakers") is True, \
            saved.get("mute") is True

    def _voiced(self) -> str:
        return self._node_id or self._local_node_id

    def _plays_on_hub(self) -> bool:
        """The voiced node's callouts play somewhere on the hub: its speakers (a peer only) or a page."""
        return bool(self._listeners) or (self._speakers and self._voiced() != self._local_node_id)

    def settings(self) -> dict[str, Any]:
        with self._lock:
            node_id, speakers, mute, muted = self._voiced(), self._speakers, self._mute, self._muted_node
        return {
            "node_id": node_id,
            "node_name": self._names(node_id),
            "speakers": speakers,
            # The saved switch, and whether the node is muted now (only while its callouts play on the hub).
            "mute": mute,
            "muted": muted == node_id,
            "local_node_id": self._local_node_id,
            # Listening pages get WAVs; without Piper they speak the text themselves.
            "piper": self._synthesize is not None,
        }

    def update(self, body: Any) -> dict[str, Any]:
        """Change `node_id` (the node picked; empty or null: the hub's own game), `speakers` and/or
        `mute`, save them and tell listening pages. Picking another node clears the mute. Raises
        ValueError for a bad body."""
        if not isinstance(body, dict) or not body.keys() & {"node_id", "speakers", "mute"}:
            raise ValueError("send node_id, speakers and/or mute")
        node_id = body.get("node_id", ...)
        if node_id is not ... and node_id is not None and not isinstance(node_id, str):
            raise ValueError("node_id must be a node id, or empty for the hub's own game")
        for name in ("speakers", "mute"):
            if name in body and not isinstance(body[name], bool):
                raise ValueError(f"{name} must be true or false")
        with self._lock:
            if node_id is not ...:
                picked = (node_id or "").strip()
                picked = "" if picked == self._local_node_id else picked
                if picked != self._node_id:
                    self._node_id, self._mute = picked, False
            if "speakers" in body:
                self._speakers = body["speakers"]
            if "mute" in body:
                self._mute = body["mute"]
            saved = {"node_id": self._node_id, "speakers": self._speakers, "mute": self._mute}
            try:
                self._settings_file.write_text(json.dumps(saved) + "\n", encoding="utf-8")
            except OSError as exc:
                self._log(f"Hub voice settings not saved to {self._settings_file}: {exc}")
            self._apply_mute()
        settings = self.settings()
        self._log(f"Hub voice: {settings['node_name']}, hub speakers {'on' if settings['speakers'] else 'off'}, "
                  f"{'muted' if settings['muted'] else 'not muted'}")
        self._tell({"type": "settings", "settings": settings})
        return settings

    def node_linked(self, node_id: str) -> None:
        """A peer linked (again): it unmuted itself when its link dropped, so mute it again if it is muted."""
        with self._lock:
            if node_id == self._muted_node:
                self._set_muted(node_id, True)

    def _apply_mute(self) -> bool:
        """Mute the voiced node while its callouts play on the hub, and unmute any other; True when it changed.
        Called under the lock."""
        target = self._voiced() if self._mute and self._plays_on_hub() else ""
        if target == self._muted_node:
            return False
        if self._muted_node:
            self._set_muted(self._muted_node, False)
        if target:
            self._set_muted(target, True)
        self._muted_node = target
        return True

    def add_listener(self, listener: Listener) -> Callable[[], None]:
        """A page listens: it gets the settings now and on change, and every voiced callout."""
        with self._lock:
            listener_id = next(self._ids)
            self._listeners[listener_id] = listener
            changed = self._apply_mute()
        if changed:
            self._tell({"type": "settings", "settings": self.settings()})
        else:
            listener({"type": "settings", "settings": self.settings()})

        def remove() -> None:
            with self._lock:
                self._listeners.pop(listener_id, None)
                changed = self._apply_mute()
            if changed:
                self._tell({"type": "settings", "settings": self.settings()})

        return remove

    def callout(self, node_id: str, text: str) -> None:
        """One callout from a node: voiced only when that node is the voiced one."""
        line = " ".join(text.split())
        with self._lock:
            if not line or node_id != self._voiced():
                return
            speakers = self._speakers
            listening = bool(self._listeners)
        if speakers and node_id != self._local_node_id:
            self._speak(line)
        if listening:
            self._run_in_background(lambda: self._clip(node_id, line))

    def _clip(self, node_id: str, line: str) -> None:
        wav = None
        if self._synthesize is not None:
            try:
                wav = base64.b64encode(self._synthesize(line)).decode("ascii")
            except Exception as exc:  # The page speaks the text itself instead.
                self._log(f"Hub voice: Piper failed, pages speak the text: {exc}")
        self._tell({"type": "callout", "node_id": node_id, "node_name": self._names(node_id), "text": line,
                    "wav": wav})

    def _tell(self, message: dict[str, Any]) -> None:
        with self._lock:
            listeners = list(self._listeners.values())
        for listener in listeners:
            listener(message)
