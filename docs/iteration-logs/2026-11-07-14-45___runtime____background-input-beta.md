# Iteration Log

- Area: `runtime`
- Title: `background-input-beta`
- Started: `2026-11-07 14:45`

## Summary

- User decision: background input (`wine_helper`) ships as a **beta**: it works, but it is not polished.
- Mouse-block experiment (`mouse_block_test.exe`, CrossOver in the macOS background, Elite kept the Win32 foreground):
  - Observe run: a fresh process took the foreground (explorer -> Elite at 403ms) and held it for 20s. `ll_moves=943 raw_input=943 cursor_moves=490`; the menu hover followed the mouse.
  - Swallow run: the hook swallowed `ll_moves=901`, but `raw_input=901` was still delivered and `cursor_moves=171`; the hover still moved.
  - So under Wine a `WH_MOUSE_LL` hook cannot block Elite's mouse. A helper mouse lock and a front-app-tied lock are dropped.
- Ruled out by the user: another macOS Space, minimizing Elite, parking the window, fake mouse injection (`SetCursorPos` warps the real cursor).

## Changes

- `docs/user/background-input.md`: Beta note at the top; new limits for the mouse (hands off the game window during routines, especially station menus) and for the 1-4s refocus wait with occasional `focus_failed`.
- Skill `edcr-background-input`: tell players about the beta limits before setup and again at hand-over.
- README: beta label on the background input doc link.
- Research 0007: mouse experiment results, conclusions and possible next steps.
- `docs/status/runtime.md`: beta caveat and follow-ups.

## Follow-ups

- Detect Mac mouse movement during menu steps: wait for idle before a menu step; on movement, back out to a known state and redo the step. Not implemented.
- Standby focus child experiment (exe and runbook exist, not run).
- Atomic replace in `install_wine_input_helper.py` (copy to a temp file, then rename).
