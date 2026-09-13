# Troubleshooting

Quick checks for when input, journal detection, or bindings look wrong.

## Contents

- [Nothing Happens When I Fire a Command](#nothing-happens-when-i-fire-a-command)
- [Galaxy Map / `dest` Navigates Incorrectly](#galaxy-map--dest-navigates-incorrectly)
- [Tail the Journal Live](#tail-the-journal-live)
- [Confirm Key Injection Works End To End](#confirm-key-injection-works-end-to-end)
- [Journal or Bindings Not Auto-Detected](#journal-or-bindings-not-auto-detected)
- [`.binds` Backup, Restore, and Presets](#binds-backup-restore-and-presets)
- [Deeper Diagnostics](#deeper-diagnostics)

## Nothing Happens When I Fire a Command

EDControlRoom sends key input to whatever window is focused. If Elite is not focused when the safety delay expires, the key presses go nowhere (or into your terminal).

- Ship-affecting commands wait **5 seconds** by default so you can click back into Elite. Switch focus in that window.
- Type `instant` in the TUI to toggle the delay off if you are operating remotely and do not need it.
- On macOS, confirm your terminal has **Accessibility** permission in System Settings.

## Galaxy Map / `dest` Navigates Incorrectly

Almost always missing arrow-key secondaries on `UI_Up / UI_Down / UI_Left / UI_Right`. See [bindings-setup.md](bindings-setup.md).

## Tail the Journal Live

```sh
uv run python3 tools/watch_journal.py
```

Prints Elite journal events as they arrive. Only useful while the game is open.

## Confirm Key Injection Works End To End

```sh
uv run python3 tools/ship_controls.py --action SetSpeedZero --delay-seconds 3
```

Waits 3 seconds, then presses the key currently bound to Elite's `SetSpeedZero` action. Focus Elite before the delay expires and expect throttle-zero to fire.

## Journal or Bindings Not Auto-Detected

Add explicit overrides in a repo-root `config.toml`:

```toml
[paths]
journal_dir = "/absolute/path/to/Journal"
bindings_file = "/absolute/path/to/Custom.4.0.binds"
```

Windows shells without `python3` on PATH: replace `uv run python3 ...` with `uv run python ...` throughout.

## `.binds` Backup, Restore, and Presets

```sh
uv run python3 tools/bindings_files.py           # inspect
uv run python3 tools/bindings_files.py backup
uv run python3 tools/bindings_files.py restore
uv run python3 tools/bindings_files.py apply-default
```

Full reference: [../operators/bindings-files.md](../operators/bindings-files.md). `apply-default` is unit-tested but not live-validated; report unexpected behavior with an issue.

## Deeper Diagnostics

- [../diagnostics/cli-reference.md](../diagnostics/cli-reference.md)
- [../diagnostics/bindings-reference.md](../diagnostics/bindings-reference.md)
- [../operators/manual-journal-routine-testing.md](../operators/manual-journal-routine-testing.md) for low-level routine validation outside Control Room.
