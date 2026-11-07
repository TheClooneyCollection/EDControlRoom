---
name: edcr-background-input
description: Set up, verify, troubleshoot or turn off EDControlRoom background input on macOS (the CrossOver wine helper), so routines drive Elite Dangerous while another Mac app is in front. Use when the user asks for background input, the wine helper, `set_input wine_helper`, or to use their Mac while routines run.
---

# EDControlRoom background input (wine helper)

You are setting up the wine helper for a player. [docs/user/background-input.md](../../../docs/user/background-input.md) is the source of truth for commands, config keys, error messages and fixes: read it before step 1 and follow it. This skill adds the order, the checks, and where to stop for the player's consent.

Work from the EDControlRoom checkout root. Every step ends on its **done** condition. Report each one to the player before moving on.

## Consent gates

Ask the player and wait for a yes before you:
- **Install software:** for example `brew install mingw-w64`.
- **Write into a CrossOver bottle:** the install step.
- **Send any input to the game:** the verification step. Also confirm that Elite is docked or in space and that they are ready.

Everything else (reading `ps`, reading files, building into `build/`, editing their local `config.toml`) is fine. Still say what you changed.

## Steps

1. **Detect the runtime.** Elite must be running. Run `ps -axo command | grep -i winewrapper | grep -i elite`:
   - the `--bottle NAME` value is the bottle;
   - the path before `/Contents/` is the CrossOver app (release `CrossOver.app` or `CrossOver Preview.app`).

   **Done:** you know the bottle name and the CrossOver app path, both read from the running process rather than guessed. If Elite isn't running, ask the player to start it. If several bottles run Elite, ask which one.

2. **Check the compiler.** Look for `x86_64-w64-mingw32-gcc` (`command -v`, then `/opt/homebrew/bin/`). If it's missing, ask before `brew install mingw-w64`.

   **Done:** the compiler path resolves.

3. **Build.** Run `uv run python3 tools/build_wine_input_helper.py`, adding `--compiler <path>` when the compiler is not at `/opt/homebrew/bin`.

   **Done:** `build/wine_input_helper/edap_input_helper.exe` exists, and `file` reports `PE32+ executable ... x86-64, for MS Windows`.

4. **Install (consent gate).** Run `uv run python3 tools/install_wine_input_helper.py --bottle <bottle>`.

   **Done:** it prints `.../<bottle>/drive_c/edap/edap_input_helper.exe` and that file exists.

5. **Configure.** Merge the `[input]` and `[input.wine_helper]` tables from the doc into the player's local `config.toml`, keeping every existing table:
   - `wine_path` is `<CrossOver app from step 1>/Contents/SharedSupport/CrossOver/bin/wine`, in TOML single quotes;
   - `bottle` is the step 1 bottle;
   - `target = "wine_helper"`.

   **Done:** `uv run python3 -c "from edap.config import load_config; c = load_config('config.toml').input; print(c.target, c.wine_helper.bottle, c.wine_helper.wine_path)"` prints `wine_helper`, the bottle and the wine path, with no `ConfigError`.

6. **Verify (consent gate).**
   - Make sure Control Room is not running (the helper serves one client), and ask the player to keep another Mac app in front.
   - Note the newest `Journal.*.log` in the journal folder and its current line count.
   - Run `uv run python3 -m tools.ship_controls --input-target wine_helper --sequence 'GalaxyMapOpen; GalaxyMapOpen delay=8'`.

   **Done:** the newly appended journal lines include a `Music` event with `MusicTrack` `GalaxyMap`, followed by another `Music` event (for example `Starport`). If only `GalaxyMap` appears, the second press probably landed while the map was loading: send `--action GalaxyMapOpen` once with the map loaded and check for the closing event, and the player confirms their front Mac app did not change. Judge by the journal, never `Status.json` `GuiFocus`. If the check fails, go to the doc's Troubleshooting section, match the exact error text, apply that fix and repeat this step.

7. **Hand over.** Tell the player:
   - Control Room now starts the helper automatically (`uv run python3 control_room.py lan` as usual);
   - `set_input foreground` switches back for a session, and the doc's "Switching back to foreground" section turns it off permanently;
   - the doc's path, for later problems.

   **Done:** the player has those three points.

## Turning it off

When the player wants foreground input back, follow the doc's "Switching back to foreground" section. Leave the installed helper in the bottle unless they ask you to remove `<bottle>/drive_c/edap/`.
