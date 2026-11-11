"""The hub voices one node's callouts (plan 0015 step 7).

Every node keeps speaking its own callouts and also sends each callout's text up the link (a `callout`
frame, live only). The hub's own game reaches it through its broker. One hub-wide setting picks the
node whose callouts the hub voices (empty: off, the default); a second switch turns on the hub
speakers. Pages that listen get each callout of that node as a message, with a Piper WAV when the hub
has Piper, else just the text for browser speech.

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

# The broker message carrying one callout (`edap.control_room.server.broker`).
ANNOUNCEMENT_MESSAGE = "event.announcement_emitted"
# A node's callout up the link: {"type": "callout", "text": ...}.
CALLOUT_FRAME = "callout"

# Hands one voice message to a listening page.
Listener = Callable[[dict[str, Any]], None]


def callout_text(message: dict[str, Any]) -> str | None:
    """The spoken text of a broker message, when it is a callout."""
    if message.get("message_type") != ANNOUNCEMENT_MESSAGE:
        return None
    payload = message.get("payload")
    text = str(payload.get("message_text") or "").strip() if isinstance(payload, dict) else ""
    return text or None


class HubVoice:
    """Hub-wide voice settings, the hub speakers and the pages listening. Thread-safe.

    `speak` queues a line on the hub's own speaker (the queue its local callouts use), `synthesize`
    turns a line into WAV bytes (None: the hub has no Piper), `run_in_background` runs synthesis off
    the caller's thread and must run work in order (one worker), `names` gives a node's name.
    """

    def __init__(
        self,
        *,
        local_node_id: str,
        settings_file: Path,
        speak: Callable[[str], bool],
        synthesize: Callable[[str], bytes] | None,
        names: Callable[[str], str],
        run_in_background: Callable[[Callable[[], None]], None],
        log: Callable[[str], None],
    ) -> None:
        self._local_node_id = local_node_id
        self._settings_file = settings_file
        self._speak = speak
        self._synthesize = synthesize
        self._names = names
        self._run_in_background = run_in_background
        self._log = log
        self._lock = threading.Lock()
        self._node_id, self._speakers = self._load()
        self._listeners: dict[int, Listener] = {}
        self._ids = itertools.count(1)

    def _load(self) -> tuple[str, bool]:
        try:
            saved = json.loads(self._settings_file.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return "", False
        except (OSError, ValueError) as exc:
            self._log(f"Hub voice settings {self._settings_file} unreadable, voice off: {exc}")
            return "", False
        if not isinstance(saved, dict):
            return "", False
        return str(saved.get("node_id") or ""), saved.get("speakers") is True

    def settings(self) -> dict[str, Any]:
        with self._lock:
            node_id, speakers = self._node_id, self._speakers
        return {
            "node_id": node_id or None,
            "node_name": self._names(node_id) if node_id else None,
            "speakers": speakers,
            "local_node_id": self._local_node_id,
            # Listening pages get WAVs; without Piper they speak the text themselves.
            "piper": self._synthesize is not None,
        }

    def update(self, body: Any) -> dict[str, Any]:
        """Change `node_id` (empty or null: off) and/or `speakers`, save them and tell listening pages.
        Raises ValueError for a bad body."""
        if not isinstance(body, dict) or not body.keys() & {"node_id", "speakers"}:
            raise ValueError("send node_id and/or speakers")
        node_id = body.get("node_id", ...)
        if node_id is not ... and node_id is not None and not isinstance(node_id, str):
            raise ValueError("node_id must be a node id, or empty for off")
        speakers = body.get("speakers", ...)
        if speakers is not ... and not isinstance(speakers, bool):
            raise ValueError("speakers must be true or false")
        with self._lock:
            if node_id is not ...:
                self._node_id = (node_id or "").strip()
            if speakers is not ...:
                self._speakers = speakers
            saved = {"node_id": self._node_id, "speakers": self._speakers}
            try:
                self._settings_file.write_text(json.dumps(saved) + "\n", encoding="utf-8")
            except OSError as exc:
                self._log(f"Hub voice settings not saved to {self._settings_file}: {exc}")
        settings = self.settings()
        self._log(f"Hub voice: {settings['node_name'] or 'off'}, hub speakers {'on' if settings['speakers'] else 'off'}")
        self._tell({"type": "settings", "settings": settings})
        return settings

    def add_listener(self, listener: Listener) -> Callable[[], None]:
        """A page listens: it gets the settings now and on change, and every voiced callout."""
        with self._lock:
            listener_id = next(self._ids)
            self._listeners[listener_id] = listener
        listener({"type": "settings", "settings": self.settings()})

        def remove() -> None:
            with self._lock:
                self._listeners.pop(listener_id, None)

        return remove

    def callout(self, node_id: str, text: str) -> None:
        """One callout from a node: voiced only when that node is the voiced one."""
        line = " ".join(text.split())
        with self._lock:
            if not line or not self._node_id or node_id != self._node_id:
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
