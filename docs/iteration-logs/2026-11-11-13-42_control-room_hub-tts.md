# Iteration Log

- Area: `control-room`
- Title: `hub-tts`
- Started: `2026-11-11 13:42`

## Summary

- Plan 0015 step 7: the hub can voice one node's callouts. Every node keeps speaking its own and also sends each callout's text up the link (live, not queued). One hub-wide setting picks the voiced node (off by default); a hub speaker switch speaks it on the hub, and a hub page that ticks "Listen here" plays it: the hub's Piper WAV, or browser speech when the hub has no Piper.

## Changes

- `edap/hub/voice.py`: `HubVoice` (settings `node_id` and `speakers`, saved to `[hub] voice_file`, default `.control_room_hub_voice.json`; `callout(node_id, text)`; listeners; injected `speak`, `synthesize`, `names`, `run_in_background`, `log`). `callout_text` reads an `event.announcement_emitted` broker message.
- Hub-wide, not per browser: the speakers are one device, and only one voiced node means two nodes never talk over each other. The hub speakers say a peer's line through the hub's own speaker queue (`HeadlessControlRoomHost.say`), so it waits behind the hub's own callouts. The hub's own node is never spoken again on the speakers (it already was); its callouts still go to listening pages through a broker listener in `serve.py`.
- Link: `PeerRelay` sends `{"type": "callout", "text"}` for each announcement its broker publishes (also with `--no-tts`, so a silent peer can be voiced by the hub). `HubLinkSession` takes a required `callout` and hands it to the voice. A callout while the link is down is gone.
- Piper: `PiperSpeechBackend.synthesize_wav` writes a line without playing it, sharing the speaker's process and lock. Clips are made on a single worker thread (`ThreadPoolExecutor(max_workers=1)`), only while a page listens, and sent base64 in the listen message (about 55 KB of base64 per short line), so there is no clip store or second fetch. Without Piper (platform voice, or `--no-tts`) `wav` is null and the page speaks the text. Piper failing logs and falls back the same way.
- Server (hub only, page token): `GET`/`POST /api/hub-voice` (`node_id`: id, or empty/null for off; `speakers`: bool; 400 otherwise, 404 off a hub), websocket `/api/hub-voice/listen` (settings first and on change, then `{type: callout, node_id, node_name, text, wav}`).
- Web: `web/hub-voice.js`, loaded by `nav.js` on a hub only, puts Voice (Off / nodes), Hub speakers and Listen here (per browser, localStorage `edcr.hubVoice.listen`) under the node picker (phones: in the More menu). Listening opens an `AudioContext` on the first tap and plays clips in order; browser speech uses the voice and rate from the haul page's speech settings. `speech.js` stays quiet while the page listens, so one device never speaks two nodes.
- Tests: in-memory link in `tests/test_hub_relay.py` (voiced node only, switch, hub node not doubled, link down, persistence, no Piper and failing Piper, HTTP and listen websocket); the `Rig` builds a `HubVoice` with recording functions. Suite: 1135 tests in 0.656-0.671 s (budget 0.681); the slowest tests are first-import warmups, nothing cheap to shave.
- Live smoke: hub and peer as two `serve` processes on loopback (peer `--no-tts`). Peer `Docked` reached the hub, a listener and the hub's `say`; hub's own `Docked` went to the listener and was spoken once; settings survived a hub restart; with `[tts.piper]` on the hub the listener got a WAV. Headless Chromium at 1280 and 390 px: panel under the picker, Listen here decoded and played a 1.0 s clip, no page errors, no horizontal scroll.

## Follow-ups

- Open point (plan): whether a node mutes itself while the hub voices it. Not built. A node-side toggle is small: a `mute` flag on `TTSAnnouncer` that skips the speaker queue but still publishes announcements (they feed the hub), plus a command or a hub-sent frame to set it.
- Announcements are published even for `disabled_messages` (only the node's own speaker honours that list), so the hub and browser speech voice them too. Filtering at publish would fix both.
- iOS stops Web Audio when the screen locks, as with `speech.js`.
