# User Docs

Start here if you want to run EDControlRoom.

1. [install.md](install.md): install Python, `uv`, and platform prerequisites.
2. [bindings-setup.md](bindings-setup.md): required Elite Dangerous key bindings. Do this once before your first run.
3. [getting-started.md](getting-started.md): the recommended way to run EDControlRoom, using the TUI plus web frontend together.
4. [haul-workflow.md](haul-workflow.md): the end-to-end `haul` workflow, including `haul.toml`.
5. [commands-reference.md](commands-reference.md): every Control Room command in one place.
6. [troubleshooting.md](troubleshooting.md): what to check when input, journal, or bindings do not behave.
7. [trade-routes.md](trade-routes.md): the web Routes page, live EDDN market prices, and how to turn the listener off.
8. [background-input.md](background-input.md): macOS + CrossOver only, optional. Let routines drive Elite while another Mac app is in front (the wine helper). Agents can set it up with the `edcr-background-input` skill.
9. [command-api.md](command-api.md): run Control Room commands over HTTP (`POST /api/command`, `POST /api/stop`) from `curl`, scripts, or automation tools.
10. [hub.md](hub.md): one home Control Room runs route searches and keeps the market DB; a Steam Deck or travel Mac points at it.

Deeper operator references (input timing, market timing, `.binds` file management, remote/multi-client mode) live under [../operators/](../operators/).
