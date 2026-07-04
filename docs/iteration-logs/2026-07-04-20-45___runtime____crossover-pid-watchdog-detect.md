# Iteration Log

- Area: `runtime`
- Title: `crossover-pid-watchdog-detect`
- Started: `2026-07-04 20:45`

## Summary

- Fixed macOS `set_pid` auto-detect selecting CrossOver `WatchDog64.exe` when its command line named `EliteDangerous64.exe` as the watchdog executable argument before the real game process row.

## Changes

- Tightened the macOS full-command-line fallback so it matches the first Windows `.exe` basename in a `ps` row instead of any later argument substring.
- Added a regression test covering the live WatchDog/Elite process-table shape where PID `23232` is the watchdog and PID `23244` is the real game process.
- Confirmed the live finder changed from `23232` to `23244` after the matcher fix.
- Updated runtime status to record that CrossOver still needs foreground HID posting because pid-targeted Quartz posting is not yet a validated background-control path.

## Follow-ups

- Investigate a different macOS/CrossOver background-input route; `set_pid foreground` remains the practical recovery path when targeted dispatch stops foreground input delivery.
