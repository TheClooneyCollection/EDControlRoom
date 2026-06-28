# Iteration Log

- Area: `control-room`
- Title: `targeted-input-targeting`
- Started: `2026-06-28 18:47`

## Summary

- Added foreground-by-default targeted-input controls so operators can switch Control Room between normal foreground dispatch and explicit pid/hwnd targeting from the command bar.

## Changes

- Extended the shared input-controller interface with target-state reporting plus `set_foreground`, `set_pid`, `set_hwnd`, and auto-detect hooks keyed by `EliteDangerous64.exe`.
- Implemented macOS pid-targeted Quartz posting and Windows hwnd/pid-targeted message dispatch while keeping the existing foreground path as the default on both platforms.
- Added Control Room `set_pid` and `set_hwnd` commands, startup/status logging, command/help discoverability updates, and regression coverage for the new backend and command flows.

## Follow-ups

- Live-validate the macOS CrossOver pid-targeted path against a backgrounded Elite window.
- Live-validate the Windows hwnd/pid path against native Elite to see whether `PostMessageW` is sufficient or whether another fallback is needed.
