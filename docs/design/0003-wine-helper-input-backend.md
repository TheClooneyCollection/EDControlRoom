# Design: `wine_helper` input backend (background keyboard input under CrossOver)

Status: accepted 2026-11-07, implementation pending. Context and decisions: [../research/0007-wine-side-background-input.md](../research/0007-wine-side-background-input.md).

Labels: **[obs]** = observed in the 2026-11-07 AHK experiment. **[repo]** = read from the code. **[inf]** = design inference that still needs validation.

## 0. Why this works (inputs to the design)

- **[obs]** With ghostty frontmost the whole time:
  - Wine reported `fg=explorer.exe` (the desktop) for the Win32 foreground.
  - `WinActivate` changed it to `EliteDangerous64.exe` with no macOS focus theft.
  - Both `SendEvent` (keybd_event) and `SendInput` then reached Elite (journal `Music GalaxyMap` / `Starport`).
- **[obs]** `ControlSend` (window messages only) had no effect, so Elite reads **raw input**. This also predicts that the native Windows `PostMessageW` hwnd path (`edcr/platform/input/windows.py:343-364`) will not work for Elite. Worth recording in runtime status.
- **[obs]** `Status.json` `GuiFocus` lags or does not update for the galaxy map. Verify with the journal `Music` event instead.
- **[inf]** AHK's `WinActivate` is more than `SetForegroundWindow`:
  - It falls back to `AttachThreadInput`.
  - As a last resort it sends an Alt keystroke.
  - We don't yet know which step succeeded under Wine. The compiled helper must log which step worked and **must never use the Alt trick**, because Alt would land in Elite.

## 1. Where it plugs in **[repo]**

- Semantic path:
  1. `ActionDispatcher.tap_action` (`edcr/actions.py:41-65`) resolves a binding through `BindingLookup`.
  2. That yields a `NormalizedBinding(key, modifier)` with internal names like `m` / `left_control` (`edcr/binding_lookup.py:120-145`).
  3. It calls `InputController.tap_key(key, modifier, hold_s)`.
- Abstract interface: `edcr/platform/input/base.py`, which already has `InputTargetState(mode=...)` plus `set_foreground_target` / `set_pid_target` / `auto_target`.
- macOS backend: `MacOSInputController` (`edcr/platform/input/macos.py:251-372`). It chooses a poster per target mode in `_dispatch_event`. Today the modes are `foreground` (HID tap) and `pid` (`CGEventPostToPid`, which is known not to work for CrossOver).
- Windows backend: it already owns **scan-code** knowledge in `KEY_CODES` (with extended keys at `windows.py:147`). That is exactly what the helper needs.
- Construction: `edcr/platform/input/factory.py` and `edcr/runtime.py:73-76,130`, with no input config today. Config dataclasses live in `edcr/config.py` (`RuntimeConfig` at `:137`), and defaults in `defaults/*.toml`.

**Proposal: add a third macOS target mode, `wine_helper`, beside `foreground` and `pid`.** Do not add a new top-level platform. Routines, bindings lookup and timing stay unchanged.

- `MacOSInputController` receives a required `WineHelperClient`-like poster callable, via the same pattern as `pid_poster`. In `wine_helper` mode it sends **scan-code** events instead of mac keycodes.
- Move the scan-code table out of `windows.py` into a shared pure module, e.g. `edcr/platform/input/scancodes.py`, used by both `windows.py` and the helper client. That gives one source of truth for Elite key names → set-1 scan codes plus the extended flag.

## 2. Helper choice: compiled Win32 exe (recommended) vs AHK v2

| | Compiled C exe (mingw-w64) | AHK v2 script |
|---|---|---|
| Sockets | Winsock directly | Needs `DllCall` into ws2_32. Clumsy, and no async. |
| Control of the activation steps | Exact: `SetForegroundWindow` → verify → `AttachThreadInput` fallback, **no Alt trick** | `WinActivate` is a black box and may emit Alt |
| Input API | `SendInput` with `KEYEVENTF_SCANCODE` (+`EXTENDEDKEY`), same as `windows.py` | `SendInput` via Send syntax, so a translation layer is needed |
| Build | `x86_64-w64-mingw32-gcc` (**installed** at `/opt/homebrew/bin`), single file, ~300 LOC | none |
| Reviewability / tests | C source in the repo, protocol tested from Python | script in the repo |
| Ships as | binary built locally by a `tools/` script (don't commit the .exe) | text file plus a third-party exe |

Recommendation: **C exe**, source at e.g. `tools/wine_input_helper/edcr_input_helper.c`, built by `tools/build_wine_input_helper.py`. Keep the AHK `bgtest.ahk` as the manual diagnostic only.

## 3. IPC

| Option | Latency | Robustness | Verdict |
|---|---|---|---|
| **TCP 127.0.0.1** (Winsock in Wine maps to host sockets) | sub-ms per message **[inf]** | Connection state gives liveness for free. Easy to reconnect. | **Use this** |
| Windows named pipe | n/a | Lives inside wineserver, so not reachable from macOS Python | no |
| AF_UNIX via Wine | ? | Wine's AF_UNIX-to-host path mapping is less proven | no |
| File drop / polling | 10-100 ms + jitter | Breaks holds, and races | no |
| Per-call `wine ... exe` | 200-800 ms startup **[inf]** | Simple, but too slow for holds and taps | launch only |

- The helper binds `127.0.0.1:<port>` only and accepts **one client at a time**.
- Auth: any local process could otherwise drive the game, so the helper requires a random token.
  - Python generates the token at launch.
  - It passes the token as a CLI arg, which is visible in `ps`. That is acceptable for local single-user use.
  - Alternative: write it to `C:\edcr\token` with 0600 perms. Pick one and document it.

## 4. Message format

Newline-delimited JSON over TCP, one request → one response, synchronous.

```
→ {"op":"hello","token":"…","protocol":1}
← {"ok":true,"helper_version":"0.1.0","protocol":1}
→ {"op":"target","process":"EliteDangerous64.exe"}
← {"ok":true,"hwnd":"0x2A01C4","pid":312}
→ {"op":"focus"}                          # re-assert Win32 fg (see §5)
← {"ok":true,"step":"already"|"set_foreground"|"attach_thread_input","fg_before":"explorer.exe"}
→ {"op":"key","scan":50,"ext":false,"down":true}
← {"ok":true}
→ {"op":"key","scan":50,"ext":false,"down":false}
← {"ok":true}
→ {"op":"release_all"}
← {"ok":true,"released":[29]}
→ {"op":"status"}
← {"ok":true,"fg":"EliteDangerous64.exe","target_alive":true,"held":[]}
→ {"op":"bye"}
```

- Errors: `{"ok":false,"error":"no_target"|"focus_failed"|"bad_token"|"bad_request","detail":"…"}`.
- **Timing stays in Python.** Holds and gaps keep coming from `TimingSampler.sample_hold` / typing delays exactly as today (`macos.py:276-311`). The helper only does individual down/up events.
  - This preserves the AGENTS.md rule that repeats are paced as separate single actions.
  - It avoids a second timing implementation.
  - Per-event round trips are sub-ms, so this stays cheap **[inf]**.
- A `seq` op (a list of events with `delay_ms`) is deliberately **left out** of v1. Add it only if measured jitter on holds is a problem.
- Modifiers are just scan-code events (LCtrl = 0x1D, RCtrl = 0x1D + ext). The mac `flags` mask is not used in this mode.

## 5. Win32 foreground handling

- **Re-assert once per burst.** `tap_key` and `press_key` send `focus` before their first key event.
  - The helper is cheap when nothing changed: if `GetForegroundWindow() == hwnd` it returns `step:"already"`.
  - This covers the user flipping CrossOver to the front and back. macdrv resets fg to the desktop on every deactivate.
- Activation order in the helper:
  1. `SetForegroundWindow(hwnd)`, then verify.
  2. Else `AttachThreadInput(cur, target_thread)` + `SetForegroundWindow` + `BringWindowToTop`, then detach and verify.
  3. Else run the same steps in a short-lived child of the helper exe (`--focus-hwnd <hwnd>`, 700ms timeout), since only freshly started processes focused reliably in live runs. Log step `child_focus`.
  4. Else return `focus_failed`.
  - Never synthesize Alt.
  - Log which step worked. Phase 1 should confirm step 1 alone suffices under Wine.
- **Do not restore the previous fg afterwards.**
  - The Win32 fg has no effect on which macOS app is front ([obs]: no focus theft).
  - Leaving Elite as the Win32 fg avoids it seeing focus-lost/focus-gained churn between bursts. Elite may pause or drop held state on focus loss **[inf]**.
- Optional later: a `focus` keepalive while a routine is running. Not needed for v1.

## 6. Launch, stop, health

Launch command (fish/sh), using the CrossOver app that **currently runs the bottle**:

```sh
"$HOME/Applications/CrossOver Preview.app/Contents/SharedSupport/CrossOver/bin/wine" --bottle Test \
  'C:\edcr\edcr_input_helper.exe' --port 47811 --token <random> --log 'C:\edcr\helper.log'
```

- Install step: `tools/install_wine_input_helper.py --bottle Test` copies the built exe to `<bottle>/drive_c/edcr/`. That is the only bottle write, and it is explicit and operator-run.
- Lifecycle modes (config `input.wine_helper.launch`):
  - `managed` (default once validated): Control Room starts the helper with `subprocess.Popen` when the operator selects the mode.
    - The operator command is `set_input wine_helper` (decided). Managed launch also starts the helper at Control Room startup when `input.target = "wine_helper"` is configured.
    - On quit, Control Room sends `bye`, waits, then terminates the Popen.
  - `manual`: the operator starts it, and Python only connects.
- Startup handshake:
  1. Connect, with retry for up to `startup_timeout_s`.
  2. `hello`: check the token and protocol.
  3. `target`.
  4. `release_all`.
  5. Then log `input target: wine helper (EliteDangerous64.exe hwnd 0x…, helper 0.1.0)` through the existing target summary (`InputTargetState.summary`, which gains a `wine_helper` branch).
- If the port is already listening with a valid handshake, reuse that helper. This covers a Control Room restart while the helper keeps running.
- Health:
  - The TCP connection is the liveness signal.
  - On any send error, reconnect once, then fail loudly.
  - `status` feeds the diagnostics output (`edcr/diagnostics.py`) and the Control Room status line.
- Orphans: if Control Room dies, the helper sees the disconnect and runs `release_all`. It then idles and accepts a new client, so the next Control Room reuses it.

## 7. Failure modes and fallbacks

| Failure | Behaviour |
|---|---|
| Helper not running / connect refused | `RuntimeError("wine helper not reachable on 127.0.0.1:47811 …")`. **Never silently fall back to the foreground HID path**: that would type Elite keys into whatever Mac app is frontmost. The operator switches explicitly with `set_pid foreground`. |
| Elite not running / window gone | `target` / `focus` returns `no_target`. The helper re-resolves the hwnd on each `focus` if `IsWindow` fails, which handles a game restart. Python surfaces the error to the routine like other dispatch failures. |
| `focus_failed` | Abort the burst before sending any key. Report the step and the current fg exe. |
| Helper crash mid-hold | Elite could keep a key held. Mitigations: (1) Python wraps every tap in try/finally and sends `key up`. (2) The helper releases all on disconnect and on `WM_ENDSESSION`/exit. (3) A watchdog in the helper auto-releases any key held longer than `max_hold_s` (default 10 s; holds today are short). (4) Python sends `release_all` after every reconnect. |
| Python crash mid-hold | The helper sees the disconnect and runs `release_all`. |
| Bottle renamed / different bottle | `bottle` is explicit config. Handshake `target` fails with `no_target`. The diagnostics command lists which bottle the running `EliteDangerous64.exe` belongs to, if that is detectable from the `ps` winewrapper path **[inf]**. |
| CrossOver Preview vs release | `wine_path` is explicit config. At launch, Python compares it with the CrossOver app path of the running `winewrapper.exe` for that bottle (visible in `ps`) and refuses on a mismatch. A different CrossOver version's wine against a live wineserver can fail with a version mismatch or start a second server **[inf]**. |
| Port in use by something else | `hello` fails (no or invalid reply). Report it and suggest changing `port`. |
| User brings CrossOver to front and types | Inputs mix, same as today's foreground mode. Not a regression. |

## 8. Config keys (new `[input]` table, e.g. `defaults/input.toml`)

```toml
[input]
# foreground | pid | wine_helper. foreground stays the default until wine_helper is validated live.
target = "foreground"

[input.wine_helper]
wine_path = ""            # required, e.g. "~/Applications/CrossOver Preview.app/Contents/SharedSupport/CrossOver/bin/wine"
bottle = ""               # required, e.g. "Test"
helper_path = 'C:\edcr\edcr_input_helper.exe'
process_name = "EliteDangerous64.exe"
port = 47811
launch = "managed"        # managed | manual
startup_timeout_s = 10.0
request_timeout_s = 1.0
max_hold_s = 10.0         # helper watchdog
```

- Empty `wine_path` / `bottle` with `target = "wine_helper"` is a validation error that names the key, following the explicit-config rule. There is no guessing.
- Validate in `edcr/config.py` next to the other `_validate_*` helpers. Use TOML literal strings for the Windows paths in tests (AGENTS.md).
- Runtime selection: `build_input_controller` takes the input config, and the mac controller starts in the configured mode. Control Room commands can still switch at runtime.

## 9. Testing

Unit tests (fast; all doubles are explicit test-local fakes; no default no-op callbacks in production signatures):

- `scancodes.py`: covers every internal key name the bindings normalizer can emit (`binding_lookup.normalize_internal_key_name`) and the extended flags. The shared Windows tests must still pass.
- Client protocol: the client takes an injected `connect` callable returning a fake stream. Assert the exact JSON lines for:
  - `tap_key("m", "left_control", hold_s=…)` → `focus`, Ctrl down, M down, M up, Ctrl up, with sampler holds via an injected sleeper;
  - `focus_failed` → no key events sent;
  - a mid-tap error → `key up` / `release_all` still sent;
  - reconnect once, then raise;
  - handshake token/protocol mismatch.
- `MacOSInputController` in `wine_helper` mode routes to the injected helper poster and never calls the HID poster. A test for "helper down → raises, no foreground fallback".
- Launcher: an injected `popen` fake. Assert the argv shape (`--bottle`, helper path, port, token), the mismatch refusal against a fake `ps` table (reuse the CrossOver `ps` fixtures from the pid-detect tests), and `bye` on shutdown.
- Config: parsing, validation errors, defaults.
- Keep each test cheap (the suite budget is 0.0006 s per test): no real sockets or sleeps in unit tests.
- Optional: a small protocol-conformance test of the C helper that runs only when an env var is set (manual, not in CI).

Manual verification (`edcr/ship_controls.py` is the human test surface):

1. Build, install, launch the helper (managed or manual), Elite docked.
2. Frontmost: ghostty. Run `ShipControls.galaxy_map_open()` (`edcr/ship_controls.py:226`) through the harness.
3. Expect a journal `Music` → `GalaxyMap`. Run it again with a delay, expect `Starport`. Expect no macOS focus change.
4. Toggle CrossOver frontmost then away (macdrv resets fg to the desktop). Repeat step 3: `focus` must report `set_foreground`.
5. Kill the helper while holding a key with a long hold. Confirm the key is released.
6. Quit Elite, then dispatch → a clear `no_target` error. Relaunch Elite → works again without restarting the helper.

## 10. Incremental plan

| # | Slice | Size |
|---|---|---|
| 1 | C helper v0: hello / target / focus (logging which step worked) / key / release_all / status. Build script with mingw. Manual protocol check with `nc` from the Mac, **GalaxyMapOpen via journal**. Confirms plain `SetForegroundWindow` suffices. | M (~300 LOC C + ~60 py) |
| 2 | Extract `scancodes.py` from `windows.py` (pure refactor; Windows tests green). | S |
| 3 | Python `WineHelperClient` + `wine_helper` mode in `MacOSInputController` + unit tests with a fake stream. | M |
| 4 | `[input]` config + validation + factory wiring + `InputTargetState.summary` branch. | S-M |
| 5 | Launcher (managed/manual), CrossOver path mismatch guard, Control Room command (`set_input wine_helper`) + help text + status line + diagnostics `status`. | M |
| 6 | Hardening: watchdog `max_hold_s`, release-on-disconnect, reconnect-once. Run manual checks 1-6. Then a live routine session (dock/undock, haul) in the background. | S-M |
| 7 | Docs: runtime status (CrossOver background input works via wine helper; `PostMessageW`/ControlSend does not reach Elite), operator doc for install/launch, iteration log. Consider making `wine_helper` the macOS default after live validation (confirm with the user first). | S |

## Resolved questions (2026-11-07)

1. The command is `set_input wine_helper`.
2. Launch is managed and automatic at Control Room start when `wine_helper` is configured.
3. The helper is built locally from C source with mingw by a repo script. No `.exe` is committed.
4. There is no native Windows helper.

The full rationale is in the research note linked at the top.
