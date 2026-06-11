# Control Room Status
## Current
- Operator-facing default text is split between `defaults/error_messages.yaml` and `defaults/messages.yaml`, with TOML overrides still supported.
- Routine failures now surface as `Failed:` plus `Try:` guidance instead of raw internal-looking error output.
- Activity-log retention and the repo-local `artifacts/control-room.log` mirror are covered in tests.
## Caveats
- Real-world validation is still needed for stale-market, wrong-station, and wrong-commodity recovery wording.
## Next
- Live-validate the new failure wording and the market back-out path against real Control Room error cases.
