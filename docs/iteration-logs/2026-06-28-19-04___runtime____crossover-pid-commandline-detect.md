# Iteration Log

- Area: `runtime`
- Title: `crossover-pid-commandline-detect`
- Started: `2026-06-28 19:04`

## Summary

- Fixed macOS `set_pid` auto-detection so CrossOver/Wine-launched Elite processes can be found even when `EliteDangerous64.exe` only appears in the full command line.

## Changes

- Kept the existing exact `ps -axo pid=,comm=` match as the first choice, then added a fallback scan over `ps -axo pid=,command=` for `EliteDangerous64.exe` in the full process arguments.
- Added focused macOS tests that cover exact command-name matches, CrossOver-style command-line-only matches, and no-match behavior.
- Re-ran the focused macOS/Control Room tests plus the full unittest suite on `main`.

## Follow-ups

- Re-test bare `set_pid` against a live CrossOver Elite session and confirm the resolved pid now receives targeted Quartz events while the game is backgrounded.
