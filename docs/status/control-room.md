# Control Room Status
## Current
- Replay-browser open/close, filter updates, selected-entry execution/edit, and default-haul toggling now route through backend intent methods alongside command submission, prompt confirmation, destination dispatch, and haul-loop launch.
- The status, haul, and market panels can now render from a backend snapshot instead of reading live app-owned state directly, which gives the existing Textual UI its first real path toward a remote backend.
- Local mode now has an always-present `LocalControlRoomBackend` that owns snapshot/event subscription for the embedded app, while the old `_protocol_event_sink` hook remains only as a compatibility passthrough for external observers like `serve`.
- Observer transport now has shared-token auth plus an app-backed `control_room connect <host>:<port>` path: authenticated `GET /capabilities`/`GET /snapshot`, `WS /session`, live `state.snapshot` updates, streamed activity/announcement events, and client-local TTS replay from streamed announcement identifiers.
- Draft protocol direction for splitting Control Room into LAN client/server mode is now documented around HTTP + WebSocket, with `serve`/`connect`, JSON envelopes, browser-friendly transport, a single active operator plus observer-clients model, client-local TTS announcement events separated from durable activity-log events, and a concrete `state.snapshot` mapping back to current Control Room models captured in `docs/design/0002-control-room-client-server-protocol.md` plus `docs/schemas/control_room_message.schema.json`.
- The first implementation slice now exists under `edap/control_room/protocol/`, with typed snapshot/event models, a `snapshot_from_app()` serializer, and protocol-native activity-log / announcement caches covered by focused tests.
- Observer-mode server now runs through `ControlRoomEventSink`, an in-memory session broker, a headless runtime host, and Starlette HTTP/WebSocket endpoints behind shared-token auth, and it now rebroadcasts merged `state.snapshot` updates as server state changes so observers do not stay on a stale initial snapshot.
- Control Room now supports `home` to route to `control_room.home_system`, and `home set` now defaults to the current live system when it is known; explicit `home set <system>` still writes that setting into config, and the example-config fallback path creates repo-root `config.toml` instead of editing `config.example.toml`.
- `haul load [path]` now supports repo-local `haul.toml` launch without prompts, the operator docs include a concrete `haul.toml` example, and replay/edit pre-fills the multi-step haul prompt directly into the command input.
- Routine failures now surface as `Failed:` plus `Try:` guidance instead of raw internal-looking output, and activity-log retention plus the repo-local `artifacts/control-room.log` mirror are covered in tests.
## Caveats
- The client/server message schema is still a draft, and replay selection plus announcement history are not yet sourced from a server session layer; the first caches still live directly on the app instance.
- `serve`/`connect` are observer-only; the app now has backend-routed panel rendering plus main operator and replay intents, but remote operator-command transport and command-history/session ownership are still not fully on a transport-neutral backend path yet.
- Real-world validation is still needed for stale-market, wrong-station, and wrong-commodity recovery wording.
## Next
- Grow the snapshot/event state out of direct app-owned lists and into a real server-owned session/state layer behind `serve`.
- Move the remaining UI surfaces and command-history/session ownership onto the backend seam so the existing Textual Control Room can graduate from observer-only remote mode into the full active remote client.
- Live-validate the new failure wording and the market back-out path against real Control Room error cases.
