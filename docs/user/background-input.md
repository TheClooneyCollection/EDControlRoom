# Background Input on macOS (wine helper)

Run routines while another Mac app is in front. By default EDControlRoom types into whichever macOS app is frontmost, so Elite has to stay in front for the whole routine. The **wine helper** is a small Windows program that runs inside your CrossOver bottle and sends keys to Elite from there, so you can keep using other Mac apps.

> Status: verified live on 2026-11-07 (CrossOver Preview, Elite docked). `foreground` stays the default until you switch.

Want your coding agent (Claude Code, Codex, ...) to set this up for you? Ask it to "set up background input". The repo ships the `edcr-background-input` skill, which walks it through the steps below.

## Contents

- [How it works and its limits](#how-it-works-and-its-limits)
- [Prerequisites](#prerequisites)
- [1. Build the helper](#1-build-the-helper)
- [2. Install it into your bottle](#2-install-it-into-your-bottle)
- [3. Configure the input table](#3-configure-the-input-table)
- [4. Start Control Room](#4-start-control-room)
- [5. Verify with the galaxy map](#5-verify-with-the-galaxy-map)
- [Switching back to foreground](#switching-back-to-foreground)
- [Troubleshooting](#troubleshooting)

## How it works and its limits

When the CrossOver window is not in front, CrossOver tells the Windows side that the desktop has focus, and Elite then ignores input. The helper makes Elite the focused window *inside* Wine before each burst of keys and sends them as real keyboard input. Your Mac's front app does not change.

How it works:
- **Semantic keys.** Keys still come from your Elite bindings, as in foreground mode; only the delivery changes.
- **One helper per Control Room.** The helper listens on `127.0.0.1` only, requires a private token, and serves one client at a time.
- **Never falls back.** If the helper is unreachable, input stops with an error instead of typing into whatever Mac app is in front.

Limits:
- **macOS + CrossOver only.** There is no native Windows or Linux version; native Windows needs real focus anyway.
- **Alt is not supported.** Bindings that use Alt are refused, because a synthesized Alt would trigger Windows menu behaviour.
- **Typing in the game window mixes input.** If you bring CrossOver to the front and type, your keys mix with the routine's, just as in foreground mode.
- **One input client at a time.** `ship_controls.py` and Control Room can't both drive the helper. Quit one before using the other.

## Prerequisites

- **CrossOver** (release or Preview), with Elite installed in a bottle.
- **mingw-w64**, to cross-compile the helper:

  ```sh
  brew install mingw-w64
  ```

  This provides `x86_64-w64-mingw32-gcc`. On Apple Silicon Homebrew it lives at `/opt/homebrew/bin/x86_64-w64-mingw32-gcc`, which is the build default. On Intel Macs, pass `--compiler x86_64-w64-mingw32-gcc`.
- **A working EDControlRoom install and bindings.** See [install.md](install.md) and [bindings-setup.md](bindings-setup.md).

Find out which bottle and which CrossOver app run Elite. Start Elite, then run:

```sh
ps -axo command | grep -i winewrapper | grep -i elite
```

- The `--bottle NAME` part is your bottle.
- The path before `/Contents/` is your CrossOver app, for example `/Users/you/Applications/CrossOver Preview.app`.

## 1. Build the helper

From the EDControlRoom checkout:

```sh
uv run python3 tools/build_wine_input_helper.py
```

This compiles `tools/wine_input_helper/edap_input_helper.c` to `build/wine_input_helper/edap_input_helper.exe`. The `build/` folder is git-ignored; no `.exe` is ever committed. Rebuild after pulling changes to the helper source.

## 2. Install it into your bottle

```sh
uv run python3 tools/install_wine_input_helper.py --bottle Test
```

Replace `Test` with your bottle name. This copies the exe to `<bottle>/drive_c/edap/edap_input_helper.exe`, which Windows sees as `C:\edap\edap_input_helper.exe`. It only writes into an existing bottle. Use `--bottles-dir` if your bottles are not in `~/Library/Application Support/CrossOver/Bottles`.

## 3. Configure the input table

Add this to your local `config.toml`, keeping the rest of the file as it is:

```toml
[input]
target = "wine_helper"

[input.wine_helper]
wine_path = '~/Applications/CrossOver Preview.app/Contents/SharedSupport/CrossOver/bin/wine'
bottle = "Test"
```

- `wine_path` must point at the `wine` inside the **same CrossOver app that is running the bottle** (Preview vs release matters). For the release app it is usually `'/Applications/CrossOver.app/Contents/SharedSupport/CrossOver/bin/wine'`.
- Use TOML single quotes for paths.

Other keys, with their defaults (see `defaults/input.toml`):

| Key | Default | Meaning |
|---|---|---|
| `helper_path` | `'C:\edap\edap_input_helper.exe'` | Where the installer put the helper, as a Windows path |
| `process_name` | `"EliteDangerous64.exe"` | The game process to send input to |
| `port` | `47811` | Loopback port for the helper |
| `launch` | `"managed"` | `managed`: Control Room starts and stops the helper. `manual`: you start it yourself and Control Room only connects. |
| `startup_timeout_s` | `10.0` | How long to wait for a freshly launched helper |
| `request_timeout_s` | `3.0` | Timeout for each request to the helper. Keep it above 2s: a `focus` can take up to about 1.7s when it falls back to a child process |
| `max_hold_s` | `30.0` | Safety watchdog: the helper releases any key held longer than this. It must be greater than `controls.market.buy_max_hold_seconds`. |
| `token_file` | `".wine_input_helper.token"` | Private token, created on first use (owner-only, git-ignored) |

## 4. Start Control Room

Start Elite first, then run Control Room as usual, e.g. `uv run python3 control_room.py lan`.

- **Managed launch:** with `target = "wine_helper"`, Control Room starts the helper in the bottle at startup.
- **Startup log:** shows the target, for example `Input target wine helper (EliteDangerous64.exe hwnd 0x..., helper 0.1.0)`.
- **Shutdown:** on quit, Control Room releases all keys and stops the helper.
- **Startup failure:** Control Room logs `Wine helper startup failed: ...` and stays on `wine_helper` with input refused. Fix the cause (see [Troubleshooting](#troubleshooting)), then run `set_input wine_helper`.

You can also switch at runtime from the command box: `set_input wine_helper`, `set_input foreground`, or `set_input pid [pid|process-name]`.

## 5. Verify with the galaxy map

Check that Elite actually receives keys while another Mac app is in front. Elite should be docked or in space, not in a menu.

1. Quit Control Room, since the harness needs the helper to itself.
2. Keep another app (e.g. Terminal) in front and run:

   ```sh
   uv run python3 -m tools.ship_controls --input-target wine_helper --sequence 'GalaxyMapOpen; GalaxyMapOpen delay=8'
   ```

   This opens the galaxy map, waits 8 seconds, then toggles it closed. Elite ignores the second press while the map is still loading, so keep the gap long; if the map stays open, run `--action GalaxyMapOpen` once more after it has loaded.
3. Check the newest journal file (`Journal.*.log` in your Elite journal folder). You should see a `"event":"Music"` line with `"MusicTrack":"GalaxyMap"`, then one with the previous track (for example `Starport` when docked). Your Mac's front app should not have changed.

Use the journal `Music` event as the check. `Status.json` `GuiFocus` lags behind and is not reliable for this.

## Switching back to foreground

- **For this session:** run `set_input foreground` in Control Room.
- **Permanently:** remove the `[input]` table or set `target = "foreground"`, then restart Control Room.

In foreground mode Elite must be the frontmost app again.

## Troubleshooting

**`wine helper not reachable on 127.0.0.1:47811; check helper launch and input.wine_helper configuration (no foreground fallback).`**
- Managed launch: check that `wine_path` and `bottle` are right, the helper was installed (step 2), and Elite is running.
- Manual launch: start the helper yourself with the token from `token_file`.
- Another program on port 47811: change `port`.
- Another client already connected: quit `ship_controls.py` or the other Control Room.

**`CrossOver app mismatch for bottle 'Test': configured ..., running ...; use the wine_path of the running CrossOver app.`**
The bottle is running under a different CrossOver app than `wine_path` points at, for example Preview vs release. Set `wine_path` to the `wine` of the running app.

**`wine helper no_target: no_target`**
- **Cause:** the helper can't find `EliteDangerous64.exe`. Elite isn't running in that bottle, or `process_name` is wrong.
- **Fix:** start Elite. The helper finds it again on the next burst, so there's no need to restart anything.

**`wine helper couldn't focus Elite inside the CrossOver bottle (focus_failed); no keys were sent.`**
In Control Room this shows as `Input to Elite failed: ...`.
- **Cause:** the helper couldn't make Elite the focused window inside Wine, even after retrying, so no keys were sent.
- **Fix:** retry. If it keeps failing, run `set_input wine_helper` to reconnect, restart Control Room to restart the helper, or run `set_input foreground` and keep Elite in front. The helper log line `focus_failed fg=<process> err=<code> child=<code>` shows which window held focus and how the child-process retry ended (`0` focused, `1` refused, `100` didn't start, `101` timed out); include it when reporting the problem.

**`wine helper refuses Alt scan code 0x38`**
- **Cause:** a binding the routine needs uses Alt.
- **Fix:** rebind it without Alt in Elite.

**`wine helper transport failed; reconnected and released all keys; interrupted input burst aborted (not replayed).`**
The connection dropped mid-burst. The helper reconnected and released every key, but the interrupted action was not repeated. Re-run the step.

**`edap_input_helper.exe` uses about 100% CPU after Control Room quits.**
- **Cause:** a helper started by an older Control Room shared its terminal, so pressing Ctrl-C to quit sent it a SIGINT too. Under CrossOver that leaves it spinning and unable to exit, even on `bye`. Control Room now starts the helper in its own session.
- **Fix:** `pkill -KILL -f edap_input_helper.exe`, then tap any key that may be held (for example LeftCtrl) once in Elite.

**Stuck keys.** The helper releases all held keys when Control Room disconnects or quits, when Elite closes, when the helper exits normally, and when any key is held past `max_hold_s`. If the helper is force-killed, it cannot clean up. Tap the stuck key once in Elite, or run `set_input wine_helper`, which releases everything when it connects.

**Check the helper log.** The helper writes `C:\edap\helper.log` inside the bottle (`<bottle>/drive_c/edap/helper.log`). It records connections and which focus step worked.
