# Iteration Log

- Area: `runtime`
- Title: `wine-helper-input-backend`
- Started: `2026-11-07 11:58`

## Summary

- Implemented the `wine_helper` macOS input mode from `docs/design/0003-wine-helper-input-backend.md`. A C helper (`tools/wine_input_helper/edap_input_helper.c`, built locally with mingw-w64, no committed `.exe`) runs in the CrossOver bottle, focuses Elite inside Wine and sends `SendInput` scan codes. Python drives it over an authenticated loopback protocol. Not yet live-validated; `foreground` stays the default.

## Changes

- **Helper:** TCP on `127.0.0.1` only, token auth, newline JSON protocol 1, one client. It refuses Alt (scan 0x38) and releases keys on disconnect, target exit, helper exit, console stop and `WM_ENDSESSION`. A 20ms watchdog releases keys held past `max_hold_s`.
- **Tools:** `tools/build_wine_input_helper.py` builds to `build/wine_input_helper/`. `tools/install_wine_input_helper.py --bottle NAME` copies the exe to `drive_c/edap/`.
- **Python:** `WineHelperClient` uses injected connect/clock/sleeper/popen/process-table/token dependencies. The `[input]` config is in `defaults/input.toml`, with `set_input wine_helper|foreground|pid`. Scan codes are shared in `edap/platform/input/scancodes.py`. There is no foreground fallback.
- **Review fixes:**
  - Only the local Control Room host and `ship_controls` start the helper. Diagnostics and `connect` clients only select the mode, so they don't take the single client slot.
  - The input-target summary no longer does a live `status` round-trip per snapshot.
  - `max_hold_s` defaults to 30s and must exceed `controls.market.buy_max_hold_seconds` (20s), so the watchdog can't cut buy holds short.
- **Docs:** user guide `docs/user/background-input.md`. The agent setup skill is at `.agents/skills/edcr-background-input/SKILL.md`, with `.claude/skills/edcr-background-input` as a relative symlink to it (git mode 120000).

## Follow-ups

- Live test on the Test bottle. Open questions:
  - whether Win32 focus works without Alt;
  - whether `wine --bottle Test` runs the console helper headless;
  - the stuck-key, watchdog and kill paths;
  - the real `ps` shape for CrossOver mismatch detection.
- Existing docs run `uv run python3 tools/ship_controls.py` directly, which fails with `ModuleNotFoundError: edap`. `python3 -m tools.ship_controls` works. Affected: `docs/user/troubleshooting.md`, `docs/operators/manual-journal-routine-testing.md`.
