# EDControlRoom

[![Tests](https://github.com/TheClooneyCollection/EDControlRoom/actions/workflows/tests.yml/badge.svg)](https://github.com/TheClooneyCollection/EDControlRoom/actions/workflows/tests.yml)
[![Discord](https://img.shields.io/badge/Discord-join%20chat-5865F2?logo=discord&logoColor=white)](https://discord.gg/73YSUBhfRG)

Multiplatform Elite Dangerous command-and-routine tooling. It handles the repetitive station-side loop of trading and hauling so the commander can stay focused on the parts that still benefit from human attention. It is **not** a hands-off flight bot.

Live-validated on **macOS** (Elite through CrossOver) and **Windows** (community-validated by CMDR VRYAE). **Linux** paths exist in the code but are not yet validated.

## Contents

- [What You Get](#what-you-get)
- [Quick Start](#quick-start)
- [Documentation](#documentation)
- [Development](#development)
- [Repo Layout](#repo-layout)
- [Contributing](#contributing)
- [License](#license)

## What You Get

- **Terminal Control Room** (TUI): live ship status, activity log, market panel, and TTS callouts for events like "ship ready to jump".
- **Web frontend**: browser UI on the same LAN for haul dashboard, Inara-backed haul search, and Spansh route fetch + comparison.
- **Haul routine**: end-to-end two-way station loop plus finite multi-leg routes.
- **Journal-driven routines**: `dock`, `undock`, `jump`, `buy`, `sell`, `dest`, `home`.

**Terminal Control Room (TUI)** — ship status, activity log, market, and haul session, with TTS callouts.

<img src="docs/assets/tui-control-room.png" alt="Terminal Control Room TUI" width="50%">

**Web dashboard** — two-way haul control with live session stats and routine progress.

<img src="docs/assets/quick-stats.png" alt="Web dashboard with haul session stats" width="50%">

**Haul search** — Inara-backed profitable route finder with one-click dispatch.

<img src="docs/assets/haul-search.png" alt="Web haul search with Inara route results" width="50%">

**Spansh route** — fetch a Spansh route and compare it side-by-side with the in-game route.

<img src="docs/assets/spansh-routes.png" alt="Spansh route fetch and comparison panel" width="50%">

## Quick Start

```sh
uv sync
uv run python3 control_room.py lan
```

`lan` starts a headless server and prints the bound URL on startup (e.g. `http://192.168.1.50:8765`). Open that URL in a browser to use the web frontend.

`lan` does **not** run a TUI or speak TTS. For TTS callouts, attach a TUI client from another terminal (same machine or another LAN box). Paste the URL `lan` printed, or use the shorter `host:port` form:

```sh
uv run python3 control_room.py connect http://<ip>:8765/ --token edcr
uv run python3 control_room.py connect <ip>:8765 --token edcr
```

Both the server and the web page default to token `edcr`, so no `--token` override is needed unless you want a different one.

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

## Contributing

Issues and PRs welcome. Before opening a PR:

- Follow Conventional Commits for commit messages.
- Run the test suite: `uv run python3 -m unittest discover -s tests`.
- If your change touches user-visible behavior, update the relevant doc under [docs/user/](docs/user/) or [docs/operators/](docs/operators/).

Bug reports and feature ideas are best filed as GitHub issues with journal / config details when relevant. Chat and questions: [Discord](https://discord.gg/73YSUBhfRG).

## License

MIT. See [LICENSE](LICENSE). This project traces back to the original ED autopilot work by SKai2 and is being maintained and reshaped for the macOS-first Control Room direction.
