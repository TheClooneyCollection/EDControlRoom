# 0011: Linux Wayland Input Backend (pure-Python uinput)

## Status

Not started. Planning only.

## Why

The current Linux input backend (`edap/platform/input/linux.py`) drives keys through `xdotool`, which only works reliably on X11 sessions. Modern Linux desktops, including SteamOS on the Steam Deck, run Wayland compositors (gamescope in Gaming Mode, KDE Plasma Wayland in Desktop Mode). On Wayland, `xdotool` is either non-functional or unreliable, so the Deck cannot use routines today.

Rather than force users into an X11 session or ship a `ydotool` daemon dependency, we want a small, self-contained key-injection backend that talks directly to `/dev/uinput`. Because uinput operates at the kernel input layer, it is compositor-agnostic: the same code works under X11, KWin-Wayland, gamescope, Sway, and any other Linux compositor.

## Approach

Write a pure-Python `/dev/uinput` client under `edap/platform/input/uinput.py`. This is a native reimplementation, not a port of `python-evdev` (whose `UInput` class delegates to a compiled `_uinput` C extension and therefore cannot be copied verbatim).

The uinput protocol is small enough to implement directly:

- `os.open("/dev/uinput", O_WRONLY | O_NONBLOCK)`.
- A fixed set of `fcntl.ioctl` calls with numeric constants from `linux/input-event-codes.h` and `linux/uinput.h`: `UI_SET_EVBIT`, `UI_SET_KEYBIT`, `UI_DEV_SETUP`, `UI_DEV_CREATE`, `UI_DEV_DESTROY`.
- Writing 24-byte `struct input_event` records for `EV_KEY` press/release plus an `EV_SYN` `SYN_REPORT` after each logical event.
- A keycode table covering the keys Elite bindings actually reference. Ported from `linux/input-event-codes.h`, not from python-evdev.

Estimated size: ~150 lines including the keycode table and docstring. No external Python dependency, no C extension.

## Scope (v1)

### In v1

- `edap/platform/input/uinput.py` implementing the `InputController` interface with the same shape as the xdotool backend.
- Keycode table sufficient for the ED bindings we already exercise on macOS/Windows (letters, digits, function keys, arrows, modifiers, space, enter, escape).
- Selection logic: prefer the uinput backend on Linux when `/dev/uinput` is writable; fall back to the xdotool backend otherwise. Runtime detection, not a hard config switch.
- Explicit config override so users can force `xdotool` or `uinput` regardless of detection.
- Unit tests for struct packing and ioctl argument construction. The real device open is guarded behind an integration test that skips when `/dev/uinput` is unavailable or unwritable (which is always the case in CI).
- Docs: `docs/getting-started/quickstart.md` Linux section updated with the udev rule and `input` group instructions, and a Steam Deck subsection noting Desktop Mode + read-only `/etc` friction.

### Not in v1

- Mouse, absolute-axis, or force-feedback event support. Elite bindings we drive are keyboard-only.
- Rewriting the xdotool backend. It stays as the X11 fallback and for machines where users cannot grant uinput permission.
- Any gamescope-specific tuning. If the kernel-level injection works, gamescope should not need special handling.
- Wayland-native protocols like `virtual-keyboard-unstable-v1` / `wtype`. Gamescope does not implement them, so they are not worth the code.

## Permission model

`/dev/uinput` is root-owned by default. Users need one of:

1. Membership in the `input` group (`sudo usermod -aG input $USER`, then re-login).
2. A udev rule that ensures `/dev/uinput` exists at boot and is group-writable:

   ```
   /etc/udev/rules.d/99-edcontrolroom-uinput.rules
   KERNEL=="uinput", GROUP="input", MODE="0660", OPTIONS+="static_node=uinput"
   ```

   Followed by `sudo udevadm control --reload-rules && sudo udevadm trigger`.

Documented recommendation: do both. The udev rule guarantees the node exists and has the right group; group membership grants access.

On SteamOS the read-only `/etc` requires `sudo steamos-readonly disable` before dropping the udev rule. Call this out in the Deck docs but do not automate it.

## Testing strategy

- CI cannot exercise the real device. GitHub runners do not expose `/dev/uinput`.
- Unit tests verify struct layout, ioctl request numbers, and the shape of the byte stream we would write for a given press/release sequence. These run on all platforms including macOS/Windows.
- Integration tests attempt to open `/dev/uinput` and skip cleanly when unavailable. On a developer or user machine with the udev rule in place, they exercise the real device.
- Manual verification: run `ship_controls.py` on a Linux/Wayland host (Steam Deck in Desktop Mode is the motivating case) and confirm ED registers input.

## Risks and open questions

- Steam Deck Gaming Mode runs gamescope under a session that may sandbox `/dev/uinput` access. Needs live verification on hardware. If Gaming Mode blocks it, Desktop Mode remains the supported target.
- Keycode coverage: we do not have a live Linux ED install to enumerate every binding. First cut covers common keys; extend as users report gaps.
- Some distros (notably Ubuntu) do not have an `input` group by default and the node is owned by `root:root`. Docs need to cover creating the group or adjusting the rule accordingly.

## Follow-ups

- Once the uinput backend is stable, retire the "xdotool preferred" language in `docs/status/runtime.md` and mark Wayland as a first-class Linux target.
- Consider whether the same backend model (kernel-level injection) could replace the current Windows or macOS input paths for consistency. Probably not worth it, but worth naming so future work does not re-litigate.
