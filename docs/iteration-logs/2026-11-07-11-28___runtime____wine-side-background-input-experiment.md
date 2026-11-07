# Iteration Log

- Area: `runtime`
- Title: `wine-side-background-input-experiment`
- Started: `2026-11-07 11:28`

## Summary

- A Wine-side injector delivers input to Elite running in CrossOver while another macOS app stays frontmost. This opens a background-input path that the macOS-side approaches (`CGEventPostToPid`, flash-focus) never did.

## Setup

- **Software:** CrossOver Preview with Elite docked in the `Test` bottle. ghostty/Terminal stayed the macOS front app the whole time.
- **Injector:** AutoHotkey v2.0.31 portable, downloaded from autohotkey.com and checked against the official `.sha256`. It is installed at `drive_c/ahk/AutoHotkey64.exe` with the test script `drive_c/ahk/bgtest.ahk` (args `<mode> [target] [key] [mods] [count]`), and stays there for now.
- **Test key:** `GalaxyMapOpen` = LeftCtrl+M.

## Results

- **`WinActivate` + `SendEvent`: worked.** The journal logged `Music` GalaxyMap at 11:25:55Z and the map opened. The script's log shows the Win32 foreground was `explorer.exe` (target inactive) before `WinActivate` and `EliteDangerous64.exe` (target active) after it. The macOS front app did not change.
- **`SendInput`: worked.** It toggled the map closed (`Music` Starport at 11:26:15Z), with the same foreground pattern and no macOS focus theft.
- **`ControlSend` (window messages, no activation): no effect.** No journal event followed, even though Wine already reported Elite as the foreground window. Elite reads raw input, not window messages. This also casts doubt on the native Windows `PostMessageW` background path.
- **Checking the result:** `Status.json` `GuiFocus` never showed 6 while the map was open; it only rewrote after the close. Verify with the journal `Music` event instead.
- **Notepad baseline:** skipped, since the Elite result was enough.

## Follow-ups

- The background-input researcher is drafting a production `wine-helper` backend design (proposal only): a resident helper in the bottle, IPC from the Python macOS backend, re-asserting the Win32 foreground before each burst, launch and stop, and failure modes.
