# Control Room Status
## Current
- Draft protocol direction for splitting Control Room into LAN client/server mode is now documented around HTTP + WebSocket, with `serve`/`connect`, JSON envelopes, browser-friendly transport, and a single active operator plus observer-clients model captured in `docs/design/0002-control-room-client-server-protocol.md` plus `docs/schemas/control_room_message.schema.json`.
- Control Room routine launchers now pass `app._time_fn` through jump/dock/undock/market/nav/haul helpers, and cached default message loads trimmed local full-suite runtime from `0.687s` to about `0.245s`.
- Single-commodity `MarketSell` totals now announce sale revenue instead of profit; haul/session profit tracking is unchanged.
- Operator-facing default text is split between `defaults/error_messages.yaml` and `defaults/messages.yaml`, with TOML overrides still supported.
- Routine failures now surface as `Failed:` plus `Try:` guidance instead of raw internal-looking error output.
- Activity-log retention and the repo-local `artifacts/control-room.log` mirror are covered in tests.
## Caveats
- The client/server message schema is still a draft; `state.snapshot` and routine argument payloads need to be tightened against real app state before implementation starts.
- Real-world validation is still needed for stale-market, wrong-station, and wrong-commodity recovery wording.
## Next
- Map current `ControlRoomApp` state/actions onto the draft protocol and decide the first active-operator handoff policy before wiring `serve` and `connect`.
- Live-validate the new failure wording and the market back-out path against real Control Room error cases.
