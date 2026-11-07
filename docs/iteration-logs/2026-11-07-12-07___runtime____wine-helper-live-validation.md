# Iteration Log

- Area: `runtime`
- Title: `wine-helper-live-validation`
- Started: `2026-11-07 12:07`

## Summary

- **The `wine_helper` input mode works live.** Elite in the CrossOver Preview `Test` bottle received keys while ghostty stayed the macOS front app.
- **Setup:** main checkout, Elite docked at Voltaire Terminal, `config.toml` `[input] target = "wine_helper"`.

## Results

- **Build and install:** OK. `build/wine_input_helper/edap_input_helper.exe` was installed to `Test/drive_c/edap/`.
- **Run 1:** `GalaxyMapOpen; GalaxyMapOpen delay=3`.
  - Press 1 opened the map (journal `Music` GalaxyMap at 12:06:57Z).
  - Press 2 had no effect, most likely dropped while the map was still loading.
  - `helper.log`: `listening`, `attach_thread_input`, `already`, `disconnected`. So the first burst needed the `AttachThreadInput` fallback after `SetForegroundWindow`.
- **Run 2:** a single `GalaxyMapOpen` with the map loaded closed it (`Music` Starport at 12:07:16Z). `helper.log`: `listening`, `already`, `disconnected`.
- **Both runs:**
  - no macOS focus theft and no Alt side effects;
  - the console helper ran headless;
  - the managed helper started for each `ship_controls` run and disconnected when it exited.
- **Skill:** Claude Code listed the `edcr-background-input` skill through the `.claude/skills` symlink.

## Changes

- The verification sequence in the user guide and the skill now uses `delay=8`, with a fallback of one extra `--action GalaxyMapOpen`.
- The guide's status line and the runtime status now record the live result. `foreground` stays the default config.

## Follow-ups

- Not yet exercised live:
  - real routines (haul);
  - Control Room auto-launch;
  - stuck-key, watchdog and kill handling;
  - a game restart;
  - the CrossOver mismatch `ps` shape.
