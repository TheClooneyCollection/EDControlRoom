# EDControlRoom

Multiplatform Elite Dangerous command-and-routine tooling. It handles the repetitive station-side loop of trading and hauling so the commander can stay focused on the parts that still benefit from human attention. It is **not** a hands-off flight bot.

Live-validated on **macOS** (Elite through CrossOver) and **Windows** (community-validated by CMDR VRYAE). **Linux** paths exist in the code but are not yet validated.

## What You Get

- **Terminal Control Room** (TUI): live ship status, activity log, market panel, and TTS callouts for events like "ship ready to jump".
- **Web frontend**: browser UI on the same LAN for haul dashboard, Inara-backed haul search, and Spansh route fetch + comparison.
- **Haul routine**: end-to-end two-way station loop plus finite multi-leg routes.
- **Journal-driven routines**: `dock`, `undock`, `jump`, `buy`, `sell`, `dest`, `home`.

**Terminal Control Room (TUI)** — ship status, activity log, market, and haul session, with TTS callouts.

![Terminal Control Room TUI](docs/assets/tui-control-room.png)

**Web dashboard** — two-way haul control with live session stats and routine progress.

![Web dashboard with haul session stats](docs/assets/quick-stats.png)

**Haul search** — Inara-backed profitable route finder with one-click dispatch.

![Web haul search with Inara route results](docs/assets/haul-search.png)

**Spansh route** — fetch a Spansh route and compare it side-by-side with the in-game route.

![Spansh route fetch and comparison panel](docs/assets/spansh-routes.png)

## Quick Start

```sh
uv sync
uv run python3 control_room.py lan
```

Uvicorn prints the bound URL on startup (e.g. `http://192.168.1.50:8765`). Open that in a browser to use the web frontend. Keep the terminal window in view for TTS callouts.

Both the server and the web page default to token `edcr`, so no `--token` is needed unless you want a different one.

**Before your first run:** set arrow-key secondaries on `UI_Up / UI_Down / UI_Left / UI_Right` in Elite. See [docs/user/bindings-setup.md](docs/user/bindings-setup.md).

Full walkthrough: [docs/user/getting-started.md](docs/user/getting-started.md).

## Documentation

- [docs/user/](docs/user/): install, bindings, getting started, haul workflow, commands, troubleshooting.
- [docs/operators/](docs/operators/): operator references (control room, remote / multi-client, bindings files, input and market timing).
- [docs/diagnostics/](docs/diagnostics/): CLI and bindings reference for diagnostics.
- [docs/status/README.md](docs/status/README.md): maintained project status entrypoint.

## Development

Use the repo `uv` environment for tests:

```sh
uv run python3 -m unittest discover -s tests
```

`main` is the active rolling-update branch; stable features and releases are marked with semantic version tags like `v1.22.0`. Commits use Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`, `chore:`).

## Repo Layout

- `control_room.py`: primary operator surface at the repo root.
- `tools/`: supported auxiliary CLIs (`run_routine.py`, `diagnostics.py`, `ship_controls.py`, bindings helpers).
- `edap/`: active runtime code.
- `tools/scratch/`: exploratory probes and one-off validation helpers.
- `archive/legacy-windows/`: historical Windows-era reference code.
