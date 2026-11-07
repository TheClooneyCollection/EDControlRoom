# Runtime Status
## Current
- Runtime config now layers ignored local `config.toml` over shipped category defaults in `defaults/*.toml`; timing still flows through a shared config-backed sampler for human-facing delays, repeat gaps, command-launch waits, key holds, and typing cadence while non-human infrastructure timing like journal polling stays deterministic.
- The macOS input backend lazily builds its pid-targeted Quartz poster and now uses `kCGEventSourceStateCombinedSessionState`; native apps like Sublime can receive background typing through it, but CrossOver/Elite still cannot.
- macOS `set_pid` auto-detect now falls back from `ps ... comm` to the full `ps ... command` line, but ignores WatchDog-style launcher rows whose first Windows `.exe` is not the requested process.
- Input backends now keep a shared foreground-by-default target model across macOS, Windows, and Linux; macOS can switch to pid-targeted Quartz posting, Windows can switch to pid/hwnd-targeted window-message dispatch, and the default auto-detect filter is `EliteDangerous64.exe`.
- `Status.json` parsing currently matches the documented ship `Flags` set; the reference docs do not define auto-docking or auto-launch bits there, so docking-computer state still has to be inferred from journal/music events rather than the status snapshot.
- macOS with CrossOver is the primary validated runtime path.
- Windows now has early real-world community validation.
- Journal tailing, bindings lookup, runtime construction, and shared platform seams are in place across supported targets.
## Caveats
- Linux remains unvalidated.
- CrossOver/Elite background input works from a Wine-side injector (2026-11-07, AutoHotkey v2 in the Test bottle, macOS front app ghostty): `WinActivate` then `SendEvent` or `SendInput` reached Elite (journal `Music` GalaxyMap/Starport) with no macOS focus theft. `ControlSend` (window messages) had no effect, and pid-targeted `CGEventPostToPid` and flash-focus failed earlier. The production backend does not exist yet, so live control still needs the macOS foreground. Use the journal `Music` event to verify, since `Status.json` `GuiFocus` lagged.
- Windows background targeting currently uses `PostMessageW` against a resolved top-level window. The CrossOver `ControlSend` result suggests Elite ignores window messages, so this path is likely ineffective until it is validated live.
- The legacy CV-driven align loop is still not ported into the active runtime.
## Next
- Live-tune the default timing distribution against real CrossOver sessions now that input delay/hold/typing jitter is centralized and operator-configurable.
- Design a production `wine-helper` input backend: a resident helper in the bottle, IPC from the Python macOS backend, and Win32 foreground re-asserted before each burst. A proposal is pending; the AHK test files stay in `drive_c/ahk/` for now.
- Live-validate the new targeted-input path on both CrossOver/macOS and native Windows, then decide whether Windows needs a stronger background-input fallback than hwnd message posting.
- Continue the portability follow-up work: CV capture/performance measurement, journal latency measurement, diagnostics/dashboard work, and broader Windows validation.
