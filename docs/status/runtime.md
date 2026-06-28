# Runtime Status
## Current
- macOS `set_pid` auto-detect now falls back from `ps ... comm` to the full `ps ... command` line, so CrossOver/Wine launches that only expose `EliteDangerous64.exe` in their arguments can still resolve the game pid.
- Input backends now keep a shared foreground-by-default target model across macOS, Windows, and Linux; macOS can switch to pid-targeted Quartz posting, Windows can switch to pid/hwnd-targeted window-message dispatch, and the default auto-detect filter is `EliteDangerous64.exe`.
- `Status.json` parsing currently matches the documented ship `Flags` set; the reference docs do not define auto-docking or auto-launch bits there, so docking-computer state still has to be inferred from journal/music events rather than the status snapshot.
- macOS with CrossOver is the primary validated runtime path.
- Windows now has early real-world validation from CMDR VRYAE.
- Journal tailing, bindings lookup, runtime construction, and shared platform seams are in place across supported targets.
## Caveats
- Linux remains unvalidated.
- Windows background targeting currently uses `PostMessageW` against a resolved top-level window, so native support exists in code but still needs live validation against Elite's real input path.
- The legacy CV-driven align loop is still not ported into the active runtime.
## Next
- Live-check `set_pid` against a real backgrounded CrossOver Elite session now that the macOS finder also scans full process arguments.
- Live-validate the new targeted-input path on both CrossOver/macOS and native Windows, then decide whether Windows needs a stronger background-input fallback than hwnd message posting.
- Continue the portability follow-up work: CV capture/performance measurement, journal latency measurement, diagnostics/dashboard work, and broader Windows validation.
