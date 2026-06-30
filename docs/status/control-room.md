# Control Room Status
## Current
- Plan 0008 is the active Control Room architecture target: one local-first `ControlRoomApp` composed with data sources, view models, view actions, and execution dependencies; local and remote execution/data-source dependencies exist, app dispatch helpers route through execution, status/haul/market panels render through data-source-backed view models without snapshot sync, market presentation commands route through view actions, and `serve` exposes authenticated no-snapshot HTTP/websocket hydrate messages on initial load and live data changes.
- Snapshot is removed from the remote wire protocol: `serve` no longer advertises or serves `/snapshot`, websocket `state.snapshot`, or `command.request_snapshot`; remaining snapshot code is internal/local compatibility pending removal.
- `connect` currently intercepts prompt-owning commands like `haul`, `haul route`, `haul search`, `dest`, `home`, `help`, `history`, and `market` locally, then sends finalized `command.dispatch_haul_loop` / `command.dispatch_destination` payloads to the headless server.
- Market panel lock semantics are aligned across embedded and `connect`: market data keeps ingesting continuously, while lock/unlock freezes or unfreezes only the displayed panel.
- `set_pid` and `set_hwnd` are available operator commands; bare forms auto-target `EliteDangerous64.exe`, explicit pid/hwnd values are accepted, and `foreground` clears the override.
- Cargo and haul session state are journal-driven: cargo manifest reads retry around transient empty `Cargo.json`, market buy/sell resync cargo, and persisted haul session totals survive relaunch unless configured otherwise.
- Remote observer clients can start without a local Elite journal path and reconnect with exponential backoff; websocket recovery relies on server hydrate messages.
- Control Room supports `home` / `home set`, repo-local `haul load [path]`, replay/edit prefill for multi-step haul prompts, and failure messages with `Failed:` plus `Try:` guidance.
## Caveats
- Known live-only connect bug: after `haul search <system>`, the observer can show the correct placeholder but an empty command bar instead of the serialized search params.
- Routine-heavy live sessions still need validation, especially targeted input with `set_pid` / `set_hwnd` under CrossOver and Windows.
- Shared LAN token auth remains acceptable for current remote work; per-user or internet-facing identity is not implemented.
## Next
- Continue plan 0008 bottom-up by moving command bar, replay browser, and trade-route picker interactions behind local view actions/data sources, then remove remaining internal snapshot compatibility.
