# Install

EDControlRoom needs Python 3.12 and, on macOS/Linux, the `uv` package manager.

## Contents

- [Platform Status](#platform-status)
- [macOS](#macos)
- [Windows](#windows)
- [Steam Deck / Linux](#steam-deck--linux)
- [Config Overrides](#config-overrides)

## Platform Status

- **macOS**: fully supported and actively used. Elite runs through CrossOver.
- **Windows**: fully supported and community-validated.
- **Steam Deck**: live-validated in Desktop and Game Mode with Elite under Proton. Other Linux desktops use the same path but are untested.

## macOS

1. Install `uv` if you do not have it: <https://docs.astral.sh/uv/getting-started/installation/>.
2. Clone this repo and `cd` into it.
3. Run `uv sync`.
4. Grant your terminal **Accessibility** permission in System Settings so it can send key input to Elite.
5. Start Elite Dangerous through CrossOver.

## Windows

With `uv` (recommended):

1. Install Python 3.12.
2. Install `uv`.
3. Clone this repo and `cd` into it.
4. Run `uv sync`.
5. Start Elite Dangerous.

Without `uv`:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Then start Elite Dangerous.

## Steam Deck / Linux

Run these in Konsole (Desktop Mode) or over `ssh`. Everything goes into your home folder, which SteamOS updates leave alone; the system partition is read-only, so do not use `sudo` or `pacman`.

1. Install `uv`: `curl -LsSf https://astral.sh/uv/install.sh | sh` (it lands in `~/.local/bin`).
2. `git clone https://github.com/TheClooneyCollection/EDControlRoom.git ~/EDControlRoom`, then `cd ~/EDControlRoom`.
3. `~/.local/bin/uv sync`. `uv` downloads Python 3.12 itself.
4. Add keyboard keys to your controller preset. Routines press keyboard keys, and the Deck's preset puts most actions on the controller only.
   - `~/.local/bin/uv run python3 tools/deck_keymap.py` shows the plan.
   - Close Elite, then rerun it with `--write`. Saving controls inside Elite rewrites the file from memory, so never write while it runs.
   - It fills only empty slots (Secondary first), keeps keys you already chose, and leaves controller bindings alone. Menu directions get arrow keys because WASD also moves the galaxy map camera. The first run saves the original as `Custom.4.2.binds.bak`; later runs never overwrite it.
   - Keys follow Elite's keyboard default where it has one (Boost `Tab`, zero throttle `X`, supercruise/jump `J`, menus arrows, `Space`, `Backspace`). Gaps take free keys: roll `,` `.`, pitch `I` `K`, full throttle `F5`, head look reset `F6`, galaxy map `F7`, supercruise-only `F8`.
5. Start Elite, then `~/.local/bin/uv run python3 tools/check_bindings.py` should report every required binding.
6. `~/.local/bin/uv run python3 control_room.py lan`, and open the printed URL from another device.

To update later: `git pull` in `~/EDControlRoom`, then `~/.local/bin/uv sync`.

No `config.toml` is needed: the journal and bindings paths are found in the Proton prefix (`compatdata/359320`). Input goes through a `/dev/uinput` virtual keyboard, which works in both Desktop Mode and Game Mode (gamescope); SteamOS already gives the `deck` user access to it. On another Linux desktop where `/dev/uinput` is not writable, either add a udev rule granting your user access or switch to `xdotool` (X11 only):

```toml
[input.linux]
backend = "xdotool"
```

## Config Overrides

Shipped defaults in `defaults/*.toml` cover most cases. Create a repo-root `config.toml` only if you need overrides. When you do, keep it minimal. Set `paths.journal_dir` and `paths.bindings_file` only if auto-detection is not enough. Leave `runtime.platform` unset unless you want to pin the backend explicitly.

Next: [bindings-setup.md](bindings-setup.md).
