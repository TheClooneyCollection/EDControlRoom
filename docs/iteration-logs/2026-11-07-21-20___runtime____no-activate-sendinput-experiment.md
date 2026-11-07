# Iteration Log

- Area: `runtime`
- Title: `no-activate-sendinput-experiment`
- Started: `2026-11-07 21:20`

## Summary

- Elite under CrossOver ignores input unless it is the Win32 foreground window. `SendInput` from inside the bottle without activating Elite did nothing; the same send with activation worked. Truly no-focus input is ruled out, and so is the virtual-gamepad route.

## Changes

- **Setup:** Test bottle, CrossOver Preview, ghostty in front, Control Room running but idle. The bottle's AHK diagnostic `drive_c/ahk/bgtest.ahk` temporarily had a `SendInputNoActivate` mode (`SendInput` without `WinActivate`). Key: `GalaxyMapOpen` (LeftCtrl+M). Checked through the journal `Music` event.
- **No activation: FAIL.** The run was valid: the log showed `fg=explorer.exe targetActive=0` at both BEFORE and SENT. No GalaxyMap `Music` line appeared and nothing happened in game. A `Starport` line 12s later was ambient docked music; the map never opened.
- **Control, `SendInput` with activation: PASS.** Elite became the Win32 foreground. GalaxyMap opened at 21:10:22 and closed at 21:10:47 (back to Starport).
- **Conclusion:** Elite does not register raw input for background delivery (no `RIDEV_INPUTSINK`-style behavior), so Win32 focus inside Wine is required. The helper's focus-then-`SendInput` design stays.
- **Gamepad route dropped.** The user reports Elite does not read controllers while in the background. Native Windows evidence agrees: community tools like joyfocus exist only to give Elite focus when a joystick moves.
- **New observation:** during the control run Elite grabbed and showed the Mac cursor, even though ghostty stayed the macOS front app. This was not recorded in earlier helper runs.
  - Likely cause (inferred, not verified): on activation Elite clips or captures the cursor (`ClipCursor` / `SetCapture` / `ShowCursor` around `WM_ACTIVATE`). winemac implements cursor clipping with a macOS event tap and cursor disassociation, which can confine the real Mac cursor even while CrossOver is not the macOS front app.
- The AHK script was restored to its previous modes afterwards.

## Follow-ups

- Check whether the wine helper's focus step causes the same cursor grab, and when it happens (docked vs flight, every activation or only the first). If it does, it hurts background use more than the hover limit does, because it takes the user's mouse away.
- Test a helper-side release: call `ClipCursor(NULL)` after focus. Clipping is global in Win32, so any process can clear it, though Elite may clip again on its next frame.
- The mouse-idle mitigation should also detect a captured cursor (for example a hidden cursor or a cursor pinned at the Elite window), not only Mac mouse movement.
