# Iteration Log

- Area: `runtime`
- Title: `steam-deck-uinput-input`
- Started: `2026-11-08 11:31`

## Summary

- First Linux validation, on a Steam Deck (SteamOS holo, Desktop Mode `kwin_x11`, Elite through Proton). The repo lives at `~/EDControlRoom` on the Deck (`/home` survives SteamOS updates) and runs with the user-installed `~/.local/bin/uv`. Journal and bindings auto-detect inside the Proton prefix (`compatdata/359320`) with no `config.toml`.
- The `deck` user has a seat ACL on `/dev/uinput`, so a kernel virtual keyboard needs no sudo or extra packages. Unlike xdotool it does not depend on X11, so it should also reach the game under Game Mode's gamescope (not yet tested).

## Changes

- New `edap/platform/input/uinput.py`: `LinuxUinputController` writes evdev key events through injected `write_key`/`close_device`; `UinputKeyboard` is the thin `/dev/uinput` adapter (stdlib `fcntl`/`struct`, device created on first key, 1s settle so the first press is not dropped). evdev codes come from the shared set-1 table, with an explicit map for extended keys and F13-F15.
- `[input.linux] backend = "uinput" | "xdotool"`, default `uinput`. xdotool stays selectable.
- Deck bindings: the Deck uses a controller preset, so 7 required actions had no keyboard binding. `tools/set_binding.py` mirrored the Mac keys (Pitch `,`/`.`, Roll `A`/`D`, `SetSpeed100` `R`, `UIFocus` LeftShift, `HeadLookReset` `G`), moved the clashing Deck keys to the Mac layout (Yaw `[`/`]`, `UpThrustButton` LeftControl), added `GalaxyMapOpen` secondary `Ctrl+M` and arrow-key `UI_*` secondaries. The original is `Custom.4.2.binds.bak`. `check_bindings` is now 19/19.

## Verification

- Live, Desktop Mode, docked: `ship_controls.py --sequence "FocusLeftPanel; UI_Back delay=3; GalaxyMapOpen delay=3; GalaxyMapOpen delay=9"` moved `GuiFocus` 0 → 2 → 0 → 6 → 0, with journal `Music` `GalaxyMap` then `Starport`.

## Follow-ups

- Test the same sequence in Game Mode (gamescope).
- uinput is foreground-only input: keys go to whatever window has focus. No pid targeting on Linux.
