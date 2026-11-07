# Iteration Log

- Area: `runtime`
- Title: `wine-helper-long-lived-focus-fix`
- Started: `2026-11-07 12:18`

## Summary

- **Bug:** in a long-running `control_room.py lan` server with Firefox in front, every routine failed with `HelperError: wine helper focus_failed`. `helper.log` showed one `attach_thread_input`, four `already`, then two `focus_failed`. The shown error was the bare text "routine unexpected exception".
- **Likely cause:** the `ship_controls` checks started a fresh helper each run, and a fresh process may take the Win32 foreground. The server's helper lives on. Once winemac moved the foreground away after Mac app switches, `SetForegroundWindow` and an `AttachThreadInput` to the target's own thread could not take it back. Not yet confirmed live.

## Changes

- **Helper (`focus_target`):**
  - 3 attempts, 30ms apart: `SetForegroundWindow`, then attach to the current foreground thread and the target thread, then `BringWindowToTop`, `SetForegroundWindow`, `SetActiveWindow` and `SetFocus`.
  - Calls `LockSetForegroundWindow(LSFW_UNLOCK)` and `AllowSetForegroundWindow(ASFW_ANY)`, and sets the foreground lock timeout to zero for the session only. Alt is still never sent.
  - A key-down that finds focus has moved re-focuses once.
  - Failures log `focus_failed fg=<process> err=<GetLastError>`.
- **Client:**
  - Retries `focus_failed` up to 3 times, 0.1s apart, and keeps the connection, since a refused focus sends no keys.
  - Raises `FocusFailed` with a readable message.
  - `close()` reconnects once to send `bye`, so a managed helper no longer outlives Control Room after an error dropped the connection.
- **Control Room:**
  - Helper errors show as `Input to Elite failed: ...`, with `set_input` recovery hints.
  - Fixed the generic routine exception lookup (`routine_unexpected_exception_message`), which had printed the bare key name instead of the error.

## Follow-ups

- Live retest in a long-running server: switch Mac apps several times between routines. If it still fails, the new `fg=` and `err=` log fields show what holds the foreground.
