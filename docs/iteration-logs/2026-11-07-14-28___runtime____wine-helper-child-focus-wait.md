# Iteration Log

- Area: `runtime`
- Title: `wine-helper-child-focus-wait`
- Started: `2026-11-07 14:28`

## Summary

- **Bug:** a routine stopped with `FocusFailed` at 14:23:36Z while the user switched and launched Mac apps. `helper.log`: 3x `focus_failed fg=explorer.exe err=5 child=101`. Since the restart there were 13 `child_focus` successes and 15 `child=101` timeouts: the child's runtime clusters around the 1.5s deadline and overruns under load. Wine process startup under Rosetta is the bottleneck. No keys were sent.

## Changes

- Helper: child focus deadline 4000ms (constant, like the other helper timings). Success is still judged by the foreground. Success logs `child_focus ms=N`; failure logs `... child=N child_ms=N`.
- Client: default `request_timeout_s` 6.0, covering a worst-case focus of about 4.2s (about 0.2s in-process plus 4s child) with margin. `FOCUS_ATTEMPTS` 3 -> 2, so a refused burst gives up after about 8.5s instead of about 13s.

## Follow-ups

- Collect `child_focus ms=` values from live runs to see the real startup distribution.
- Pre-warmed standby focus child experiment (runbook with the mouse-block test) to see whether an idle child keeps foreground rights.
