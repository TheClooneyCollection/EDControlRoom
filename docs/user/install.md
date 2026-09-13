# Install

EDControlRoom needs Python 3.12 and, on macOS/Linux, the `uv` package manager.

## Contents

- [Platform Status](#platform-status)
- [macOS](#macos)
- [Windows](#windows)
- [Linux (untested)](#linux-untested)
- [Config Overrides](#config-overrides)

## Platform Status

- **macOS**: fully supported and actively used. Elite runs through CrossOver.
- **Windows**: fully supported and live-validated by community member CMDR VRYAE.
- **Linux**: runtime paths exist but are not live-validated. Expect small adjustments (paths, input backend) before it works end to end. See the note at the bottom of this page.

## macOS

1. Install `uv` if you do not have it: <https://docs.astral.sh/uv/getting-started/installation/>.
2. Clone this repo and `cd` into it.
3. Run `uv sync`.
4. Grant your terminal **Accessibility** permission in System Settings so it can send key input to Elite. Grant **Screen Recording** as well if you plan to use capture-based diagnostics.
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

## Linux (untested)

1. Install Python 3.12 and `uv`.
2. Install `xdotool` for synthetic key input. The Linux input path is X11-oriented; Wayland is unverified.
3. Start Elite Dangerous through Steam / Proton.

If auto-detection does not find the Proton journal directory, set `paths.journal_dir` and `paths.bindings_file` explicitly in a repo-root `config.toml`. Minimal example:

```toml
[paths]
journal_dir = ""
bindings_file = ""

[tts]
title_mode = "custom"
title = "captain"
```

Linux input is currently implemented through `xdotool`. Wayland behavior is unverified.

## Config Overrides

Shipped defaults in `defaults/*.toml` cover most cases. Create a repo-root `config.toml` only if you need overrides. When you do, keep it minimal. Set `paths.journal_dir` and `paths.bindings_file` only if auto-detection is not enough. Leave `runtime.platform` unset unless you want to pin the backend explicitly.

Next: [bindings-setup.md](bindings-setup.md).
