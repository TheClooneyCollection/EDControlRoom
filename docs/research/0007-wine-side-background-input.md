# Wine-Side Background Input for CrossOver

Date: 2026-11-07

Status: accepted 2026-11-07, implementation pending.

Design: [../design/0003-wine-helper-input-backend.md](../design/0003-wine-helper-input-backend.md)

## Goal

Let Control Room routines drive Elite Dangerous running in CrossOver while another macOS app is frontmost. The user wants to use other Mac apps while routines run. Today every routine needs the CrossOver window in the macOS foreground, so the Mac can't be used for anything else during a haul.

## Context

### Prior failures (macOS side)

- **Foreground HID posting** (the current default) works only while CrossOver is the frontmost macOS app.
- **Pid-targeted posting** (`CGEventPostToPid` with `kCGEventSourceStateCombinedSessionState`) delivers background input to native apps like Sublime, but not to CrossOver/Elite.
- **Flash-focus** (briefly bringing CrossOver to the front around each burst) also failed as a background-control path, and it steals focus anyway.

### Root cause

- winemac (the CrossOver macOS driver) sets the Win32 foreground window to the desktop (`explorer.exe`) whenever the CrossOver app is deactivated on macOS.
- Elite gates input on having Win32 focus, so events that arrive while it is not the Win32 foreground window are ignored, whichever macOS route delivers them.
- The Win32 foreground inside Wine is separate from the macOS front app. A process inside the bottle can make Elite the Win32 foreground window without activating CrossOver on macOS.

### 2026-11-07 experiment

Setup:
- **Environment:** CrossOver Preview, with Elite docked in the `Test` bottle. ghostty/Terminal was the macOS front app throughout.
- **Injector:** AutoHotkey v2.0.31 portable, downloaded from autohotkey.com and checked against the official `.sha256`, run inside the bottle (`drive_c/ahk/bgtest.ahk`).
- **Key:** `GalaxyMapOpen` (LeftCtrl+M).

| Method | Result |
|---|---|
| `WinActivate` + `SendEvent` | **Worked.** Journal `Music` GalaxyMap at 11:25:55Z, and the map opened. The script log showed the Win32 foreground was `explorer.exe` before `WinActivate` and `EliteDangerous64.exe` after it. The macOS front app did not change. |
| `WinActivate` + `SendInput` | **Worked.** It toggled the map closed (`Music` Starport at 11:26:15Z), with the same foreground pattern and no macOS focus theft. |
| `ControlSend` (window messages, no activation) | **No effect** (no journal event), even though Wine already reported Elite as the foreground window. |

Conclusions:
- Elite reads raw input, not window messages. This suggests the native Windows `PostMessageW` background path is ineffective for Elite as well.
- Activating the window inside Wine, followed by synthesized raw input from inside the bottle, is enough, and it does not steal macOS focus.
- `Status.json` `GuiFocus` is not a reliable check: it never showed 6 while the map was open and only rewrote after the close. Use the journal `Music` event to verify.

### 2026-11-07 mouse experiment

Problem: menu routines desync because the Mac mouse moving over the Elite window moves Elite's menu hover, even with CrossOver in the macOS background (the helper keeps Elite the Win32 foreground). Moving Elite to another macOS Space does not help.

Test: a standalone exe in the bottle installed a `WH_MOUSE_LL` hook, counted raw input (`RIDEV_INPUTSINK`) and cursor moves, and kept Elite the Win32 foreground. CrossOver was in the macOS background in both rounds.

| Round | Result |
|---|---|
| Observe only | A fresh process took the foreground (explorer -> Elite at 403ms), and Elite kept it for all 20s. `ll_moves=943`, `raw_input=943`, `cursor_moves=490`. The menu hover followed the mouse. |
| Hook swallows everything | The hook swallowed `ll_moves=901`, but `raw_input=901` was still delivered and `cursor_moves=171`. The menu hover still moved. |

Conclusions:
- Under Wine a `WH_MOUSE_LL` hook cannot block Elite's mouse: wineserver delivers raw input independently of the LL hook, and the Win32 cursor follows the real Mac cursor. So a helper mouse lock, and a Python lock tied to the macOS front app, are dropped.
- Also ruled out: another macOS Space, minimizing Elite (not possible), parking the window out of the way, and injecting a fake mouse (`SetCursorPos` would warp the player's real cursor).
- Shipped as beta with a documented "keep the mouse off the game window" limit.
- Not done, possible next steps:
  - Detect Mac mouse movement during menu steps: wait for the mouse to be idle before a menu step, and on movement, back out to a known state and redo the step.
  - Pre-warmed standby focus child: an experiment exe and runbook exist, but it was not run. It would show whether a child started earlier keeps foreground rights, which would take the about 0.7-4s Wine startup off the focus path.


1. **`set_input wine_helper`** is the operator command. It selects a third macOS input target mode beside `foreground` and `pid`. Dispatch, bindings lookup and timing stay unchanged.
2. **Managed auto-launch.** When the `wine_helper` input mode is configured, Control Room starts the helper in the bottle at startup and stops it on quit.
3. **Written in C.**
   - Not Python: that would need a Windows Python installed in the bottle.
   - Not Rust: it needs an extra `x86_64-pc-windows-gnu` target, the `windows-sys` crate and a heavier toolchain for a helper of about 300 lines.
   - The `x86_64-w64-mingw32-gcc` toolchain is already installed.
4. **Local build from source.** A repo script cross-compiles the C source on macOS to an x86_64 Windows exe. No `.exe` is committed.
5. **No native Windows helper.** Native Windows needs real focus anyway, so it has no equivalent of the Wine trick (setting the Win32 foreground without activating the app on macOS).
6. **Foreground stays the default** input mode until `wine_helper` is validated live. Making it the macOS default later needs the user's confirmation.
7. **No silent fallback to foreground input** when the helper fails. A fallback would type Elite keys into whatever Mac app is frontmost. Helper failures raise clear errors, and the operator switches modes explicitly.

## Notes

- The AHK test files stay in the bottle (`drive_c/ahk/`) for now as a manual diagnostic. They are not part of the production path.
