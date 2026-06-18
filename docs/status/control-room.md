# Control Room Status
## Current
- Control Room now supports `home` to route to `control_room.home_system`, and `home set` now defaults to the current live system when it is known; explicit `home set <system>` still writes that setting into config, and the example-config fallback path creates repo-root `config.toml` instead of editing `config.example.toml`.
- The operator docs now include a concrete `haul.toml` example and `haul load [path]` guidance, so the text-editable haul-profile flow is discoverable from user-facing docs instead of only command help and status notes.
- Control Room `haul` now supports `haul load [path]`, which reads repo-local `haul.toml` by default and launches the normal two-way haul routine without stepping through the interactive prompt.
- Replay/edit of haul entries now opens the multi-step haul prompt with the existing answers prefilled directly into the command input, so operators can edit or clear fields instead of fighting placeholder-only defaults.
- Control Room routine launchers now pass `app._time_fn` through jump/dock/undock/market/nav/haul helpers, and cached default message loads trimmed local full-suite runtime from `0.687s` to about `0.245s`.
- Single-commodity `MarketSell` totals now announce sale revenue instead of profit; haul/session profit tracking is unchanged.
- Operator-facing default text is split between `defaults/error_messages.yaml` and `defaults/messages.yaml`, with TOML overrides still supported.
- Routine failures now surface as `Failed:` plus `Try:` guidance instead of raw internal-looking error output.
- Activity-log retention and the repo-local `artifacts/control-room.log` mirror are covered in tests.
## Caveats
- Real-world validation is still needed for stale-market, wrong-station, and wrong-commodity recovery wording.
## Next
- Live-validate the new failure wording and the market back-out path against real Control Room error cases.
