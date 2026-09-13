# EDControlRoom

[![Tests](https://github.com/TheClooneyCollection/EDControlRoom/actions/workflows/tests.yml/badge.svg)](https://github.com/TheClooneyCollection/EDControlRoom/actions/workflows/tests.yml)
[![Discord](https://img.shields.io/badge/Discord-join%20chat-5865F2?logo=discord&logoColor=white)](https://discord.gg/73YSUBhfRG)

Multiplatform Elite Dangerous command-and-routine tooling. It handles the repetitive station-side loop of trading and hauling so the commander can stay focused on the parts that still benefit from human attention. It is **not** a hands-off flight bot.

Live-validated on **macOS** (Elite through CrossOver) and **Windows** (community-validated by CMDR VRYAE). **Linux** paths exist in the code but are not yet validated.

## Contents

- [The Idea](#the-idea)
- [What You Get](#what-you-get)
- [Quick Start](#quick-start)
- [Documentation](#documentation)
- [Development](#development)
- [Repo Layout](#repo-layout)
- [Contributing](#contributing)
- [License](#license)

## The Idea

A co-pilot, not an autopilot. You stay focused on flying; EDControlRoom takes over anything that lives behind a game menu.

The flagship is the **two-way haul routine**. When your ship drops near a station, it handles the boring bits end to end: request docking, work through station services, sell, refuel and repair, buy the return cargo, set the next-leg route, undock, clear mass lock, and prime the FSD. When the drive is primed it uses TTS to call the commander by title or name and announce the ship is ready to jump — that is your cue to take over for alignment and the next jump.

That makes it a direct fit for high-volume A↔B cargo work like community goal loops or long chill hauls, where the station-to-station cycle is the part worth automating and human attention is better spent on flying.

![Hauling in VR with EDControlRoom's help](docs/assets/haul-vr.png)

**See it in action:** [live stream demo — co-pilot handling a station cycle](https://www.youtube.com/live/YKbz7xtc22Q?t=6014s)

[![EDControlRoom co-pilot demo](https://img.youtube.com/vi/YKbz7xtc22Q/hqdefault.jpg)](https://www.youtube.com/live/YKbz7xtc22Q?t=6014s)

## What You Get

A terminal Control Room with TTS callouts, a LAN web frontend for haul dashboard / search / Spansh routing, and journal-driven `dock`, `undock`, `jump`, `buy`, `sell`, `dest`, `home`.

_(Expand / click the following sections to see the screenshots.)_

<details>
<summary><strong>Terminal Control Room (TUI)</strong> — ship status, activity log, market, and haul session, with TTS callouts.</summary>

- Live panels: SHIP STATUS (commander, system, station, fuel, cargo, FSD target), ACTIVITY log, and MARKET table from `Market.json`.
- Full command bar for `dock`, `undock`, `jump`, `buy`, `sell`, `dest`, `home`, `travel`, `market ...`.
- Start haul work from the command bar: `haul [commodity]`, `haul start`, `haul load`, `haul search [system]`, `haul search url <inara-url>`, `haul route <n>`, `multi_leg_haul <route>`.
- `pause` / `resume` an active two-way haul; `stop` and `new_session` control the persisted session timer / profit.
- `Ctrl-R` reopens replay / command history; `Ctrl-C` interrupts (haul-aware safe stop first, cancel on second).
- Speaks TTS callouts locally, e.g. "commander, ship ready to jump" at the end of a leg.

<img src="docs/assets/tui-control-room.png" alt="Terminal Control Room TUI" width="50%">
</details>

<details>
<summary><strong>Web dashboard</strong> — two-way haul control with live session stats and routine progress.</summary>

- Quick stats strip: home system, current system, destination, cargo, routine, completed runs, session profit.
- Active routine board with the five haul stages (Buy, Undock, Depart, Transit, Sell) plus elapsed, current / accumulated credits, and cargo moved.
- Active route panel: jumps remaining, LY remaining, boosts remaining for the dispatched Spansh route.
- Header controls: **Pause**, **Resume**, **Stop after run**, **Stop now**, **Save** the current haul as the default, **Reconnect**, and **Instant off** for the 5-second safety delay.

<img src="docs/assets/quick-stats.png" alt="Web dashboard with haul session stats" width="50%">
</details>

<details>
<summary><strong>Haul search</strong> — Inara-backed profitable route finder with one-click dispatch.</summary>

- Filter by origin (and optional destination), max route distance with presets, station distance, cargo capacity, profit metric, and min supply / demand.
- Results sort by profit / hour or profit / trip and show cargo, both stations, distance, and route LY.
- **Start route** hands the selected pair to the two-way haul routine; **Set destination** just routes there; **Travel assist** flies to an arbitrary system + station without hauling.
- Same search is reachable from the TUI via `haul search [system]` and `haul search url <inara-url>`; `haul route <n>` picks a numbered result.
- Note: v1 excludes surface / land settlements — station and carrier routes only.

<img src="docs/assets/haul-search.png" alt="Web haul search with Inara route results" width="50%">
</details>

<details>
<summary><strong>Spansh route</strong> — fetch a Spansh route and compare it side-by-side with the in-game route.</summary>

- Inputs: from / to system, jump range (LY, unladen), efficiency, supercharge mode, optional final station, all-in-one navroute wait, and compare retries.
- **Fetch Spansh** to pull a route, **Set in-game route** to plot it in Elite via the galaxy map, **Compare** to diff Spansh vs the plotted route jump-by-jump, or **All in one** to run the full flow.
- **Switch to Spansh** hands the fetched route to the active haul so the dashboard's Active route panel drives jumps remaining / LY remaining / boosts.
- Route detail table shows system, neutron flag, +LY per jump, and cumulative total for both routes side by side.

<img src="docs/assets/spansh-routes.png" alt="Spansh route fetch and comparison panel" width="50%">
</details>

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
