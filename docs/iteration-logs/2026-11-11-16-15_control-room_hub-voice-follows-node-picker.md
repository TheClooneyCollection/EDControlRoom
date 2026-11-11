# Iteration Log

- Area: `control-room`
- Title: `hub-voice-follows-node-picker`
- Started: `2026-11-11 16:15`

## Summary

- The hub voice panel was confusing (a separate Voice dropdown beside the node picker). The voiced node is now the node picked in the node picker, saved hub-wide on every pick; nothing picked means the hub's own game. The panel has Play on hub speakers (hidden when the hub itself is picked), Play in this browser and a new Mute <node>, which makes the node stop speaking its own callouts so they play only on the hub. Resolves the plan 0015 "mute" open point.

## Changes

- `edap/hub/voice.py`: `HubVoice` keeps `node_id` ("" = hub's own game), `speakers` and `mute` (saved in `[hub] voice_file`; an old file with only `node_id`/`speakers` loads as before). Picking another node clears `mute`. The node is muted only while its callouts play on the hub (hub speakers on for a peer, or any listening page); `_apply_mute` runs on every settings change and listener add/remove, unmuting the old node before muting a new one. `node_linked` re-mutes a peer that reconnects. New required `set_muted(node_id, muted)` dep, built by `node_muter` (local: direct; peer: `voice_mute` frame via the new `HubRelay.send`). Settings now return `mute` and `muted` (in effect), and `node_id` is never null.
- Link: `voice_mute` (hub to peer, `{muted}`) is a hub relay frame; `PeerLink.on_frame` routes it and `PeerRelay` calls its new required `set_muted(bool)`, logs the change, and unmutes on `link_down`. `HubLinkSession` takes a required `linked(node_id)`, called after the relay attach.
- Node side: `TTSAnnouncer.muted` skips the speaker queue for callouts (`say` still speaks, so the hub's own voicing of a peer is unaffected); `HeadlessControlRoomHost.mute_callouts`. The broker's `mute_callouts` stamps `muted: true` on `event.announcement_emitted` (schema: optional boolean; `AnnouncementEvent.muted`), so `web/speech.js` and `connect` TUIs skip muted lines, including the server-published Spansh route callout. The text still goes up the link (`callout_text` ignores the flag). `serve.py` wires one `mute_own_callouts` for both the peer relay and the hub's own game.
- Web: `nav.js` POSTs the picked node to `/api/hub-voice` before reloading. `hub-voice.js` lost the dropdown; helper line "Each machine speaks its own callouts. These play the picked node's callouts here too."; the mute box is enabled only while a play box is on (or it is already ticked, so it can be unticked). If another browser picked a different node since, the status says so and a "Voice <node> instead" button re-picks this page's node.
- Docs: `docs/user/hub.md` voice section rewritten; plan 0015 TTS section gains an as-built note and the open point is resolved.
- Tests: `tests/test_hub_relay.py` (picked node voiced, hub default, mute only while playing, unmute on link drop and re-mute on relink, unmute on speakers off / listener gone / node change, local mute, broker stamping), `tests/test_tts.py` (muted announcer still says free text), `tests/test_control_room_client.py` (TUI skips muted announcements). Suite: 1149 tests in 0.622 s (budget 0.689).
- Live smoke: hub `serve` from a scratch config with an old voice file (`node_id` of a missing peer, speakers on) loaded fine. Headless Chrome `--dump-dom`: panel shows the three boxes, "(picked in another browser)" and the "Voice <hub> instead" button; with the hub picked, Play on hub speakers is hidden. Over the API with mute on and the hub picked: `muted` false with no listener, true while a websocket listener is open, false after it closes.

## Follow-ups

- Mute with Play on hub speakers on a hub started with `--no-tts` (or no speech backend) would still mute the peer while the hub cannot speak; not guarded.
- A node's own pages show no hint that it is muted by the hub (they just stay quiet).
- Not yet tried with two machines or with clicks in a real browser.
