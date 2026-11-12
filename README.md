<h1 align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logos/hyperspace-trail-wordmark-dark.png">
    <source media="(prefers-color-scheme: light)" srcset="assets/logos/hyperspace-trail-wordmark-light.png">
    <img src="assets/logos/hyperspace-trail-wordmark-light.png" alt="EDControlRoom" width="640">
  </picture>
</h1>

[![Tests](https://github.com/TheClooneyCollection/EDControlRoom/actions/workflows/tests.yml/badge.svg)](https://github.com/TheClooneyCollection/EDControlRoom/actions/workflows/tests.yml)
[![Release](https://img.shields.io/github/v/release/TheClooneyCollection/EDControlRoom)](https://github.com/TheClooneyCollection/EDControlRoom/releases/latest)
[![License](https://img.shields.io/github/license/TheClooneyCollection/EDControlRoom)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![Platforms](https://img.shields.io/badge/platforms-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey)](#quick-start)
[![Discord](https://img.shields.io/badge/Discord-join%20chat-5865F2?logo=discord&logoColor=white)](https://discord.gg/73YSUBhfRG)

<table>
  <tr>
    <td width="50%" align="center" valign="top"><a href="docs/assets/screenshots/intro-markets.png"><img src="docs/assets/screenshots/intro-markets.png" alt="Markets page comparing recent markets"></a><br><sub>Markets page</sub></td>
    <td width="50%" align="center" valign="top"><a href="docs/assets/screenshots/intro-routes.png"><img src="docs/assets/screenshots/intro-routes.png" alt="Routes page ranking round trips"></a><br><sub>Routes page</sub></td>
  </tr>
  <tr>
    <td width="50%" align="center" valign="top"><a href="docs/assets/screenshots/intro-inara-search.png"><img src="docs/assets/screenshots/intro-inara-search.png" alt="Integrated Inara haul search"></a><br><sub>Integrated Inara search</sub></td>
    <td width="50%" align="center" valign="top"><a href="docs/assets/screenshots/intro-two-way-haul.png"><img src="docs/assets/screenshots/intro-two-way-haul.png" alt="Two-way haul page with a haul running"></a><br><sub>Two-way haul</sub></td>
  </tr>
</table>

A control room for Elite Dangerous traders and haulers, on any device on your LAN.

- **Live market data, locally.** Your own EDDN database: about 40 MB for 10,000+ markets.
- **Routes page.** Powered by that database: round trips ranked by profit per hour, near you or galaxy-wide.
- **Markets page.** The best deal between any two markets you visited, priced for your ship.
- **Inara search.** Built into the haul page, one click to a route.
- **Hub.** Every machine in one place: one tab, one database, one haul history (see [Hub](#hub-connected-intelligence)).
- **Haul history.** Profit per hour by route, commodity and ship. **Track only** counts the trips you fly and trade by hand, with no keys sent.
- **Voice callouts.** Piper or system voice, on the game machine, the hub or a phone.
- **Assisted haul loop.** Optional, see the [Terms of Use warning](#assisted-haul-loop).

## Contents

- [What You Get](#what-you-get)
- [Quick Start](#quick-start)
- [Hub: Connected Intelligence](#hub-connected-intelligence)
- [Steam Deck](#steam-deck)
- [Piper Voice](#piper-voice)
- [Assisted Haul Loop](#assisted-haul-loop)
- [Documentation](#documentation)
- [Development](#development)
- [Repo Layout](#repo-layout)
- [Contributing](#contributing)
- [License](#license)

## What You Get

A LAN web frontend (markets and Best deal, EDDN trade routes, haul search, two-way haul, one-tap controls, Spansh travel), a terminal Control Room, haul history, TTS callouts, a multi-machine hub, and journal-driven `dock`, `undock`, `jump`, `buy`, `sell`, `dest`, `home`.

_(Expand a section for details.)_

<details>
<summary><strong>Web dashboard</strong> — two-way haul control with live session stats, routine progress and haul history.</summary>

- Quick stats strip: home system, current system, destination, cargo, routine, completed runs, session profit.
- Active routine board with the five haul stages (Buy, Undock, Depart, Transit, Sell) plus session elapsed, current / accumulated credits, cargo moved, and this run / last run / average run times.
- **History** panel: every run is saved, completed or aborted. Today / 48h / Week / Month / All tabs show total profit, profit per hour, time and runs, with routes, commodities and a journal trade ledger under Details.
- Header controls: **Pause**, **Resume**, **Stop after run**, **Stop now**, **Save** the current haul as the default, **Reconnect**, and **Instant off** for the 5-second safety delay.
- **Copy / paste route** moves a route between Control Rooms, for example from a machine that can run the Inara search to a Steam Deck, or to a friend.

<img src="docs/assets/screenshots/two-way-haul.png" alt="Web dashboard with haul session stats and history" width="50%">
</details>

<details>
<summary><strong>Haul search</strong> — Inara-backed profitable route finder with one-click dispatch.</summary>

- Filter by origin (and optional destination), max route distance with presets, station distance, cargo capacity, profit metric, surface stations, and min supply / demand.
- Results sort by profit / hour or profit / trip and show cargo, both stations, distance, and route LY.
- **Start route** hands the selected pair to the two-way haul routine; **Track only** just tracks it while you fly and trade by hand (session stats, stages and history from the journal, no keys sent); **Set destination** just routes there; **Travel assist** flies to an arbitrary system + station without hauling.
- Same search is reachable from the TUI via `haul search [system]` and `haul search url <inara-url>`; `haul route <n>` picks a numbered result.
- **Surface stations** picks Inara's planetary filter: No (default), Yes excluding Odyssey settlements, or Yes with them.
</details>

<details>
<summary><strong>Markets</strong> — the last markets you opened, and the best deal between any two of them.</summary>

- `/markets` lists the last 20 stations whose commodities market you opened (`[control_room] recent_markets_limit`), with the full market table for each. On a hub the list holds every machine's markets.
- **Best deal** compares two of them for your hold: the top 3 commodities each way, ranked by full-hold profit, with profit per ton, per trip and per hour.
- **Copy route** or **Open in haul** runs the picked round trip as a two-way haul.

<img src="docs/assets/screenshots/markets-best-deal.png" alt="Markets page with best deal" width="50%">
</details>

<details>
<summary><strong>Trade routes (EDDN)</strong> — round-trip routes from live market prices, no Inara needed.</summary>

- With `[eddn] enabled = true` the `lan` server listens to EDDN and keeps a local price database; the server log prints a status line every 30 s.
- `/routes` ranks round trips by profit / hour: **Near** (from your system) or **Global**, sized by 1 / 2 / 4 jumps or 100 / 250 Ly, with supply, station distance and data age filters (demand is not filtered: any listed sell price counts).
- **Copy** a route and paste it into the haul page's **Copy / paste route** box to run it.
- **Open in haul** loads a route straight into `/haul`. Markets you open in game go into the same database, so stations nobody uploaded still count.
- Details and how to turn it off: [docs/user/trade-routes.md](docs/user/trade-routes.md).

<img src="docs/assets/screenshots/eddn-routes.png" alt="EDDN routes page" width="50%">
</details>

<details>
<summary><strong>Controls</strong> — one-tap ship routines without the haul page.</summary>

- `/controls` has buttons for undock, dock, jump, escape and boost, buy / sell by commodity, sell all cargo, and a big red **STOP NOW**.
- Nav panel: plot a route, travel to a system and station, plot or set home.
- Voice panel: say any line, pick a Piper voice and tune it live.
- Each panel shows `Idle` or `Busy: <routine>`, and routine buttons disable while something runs.

<img src="docs/assets/screenshots/quick-controls.png" alt="Controls page" width="50%">
</details>

<details>
<summary><strong>Spansh route</strong> — fetch a Spansh route and compare it side-by-side with the in-game route.</summary>

- Lives on the `/travel` page (sidebar **Ship → Travel**; on phones under the **More** menu).

- Inputs: from / to system, jump range (LY, unladen), efficiency, supercharge mode, optional final station, all-in-one navroute wait, and compare retries. From, jump range, and supercharge mode auto-fill from live ship state (current system + Loadout event); wait / retries auto-fill from server config.
- **Fetch Spansh** to pull a route, **Set in-game route** to plot it in Elite via the galaxy map, **Compare** to diff Spansh vs the plotted route jump-by-jump, or **All in one** to run the full flow.
- **Switch to Spansh** starts the standalone Spansh route runner: it flies the fetched route waypoint by waypoint, and every time you arrive at a waypoint it automatically sets the galaxy map to the next one.
- Route detail table shows system, neutron flag, +LY per jump, and cumulative total for both routes side by side. The Active route panel at the top of `/travel` tracks jumps remaining / LY remaining / boosts while the runner is active.

<img src="docs/assets/spansh-routes.png" alt="Spansh route fetch and comparison panel" width="50%">
</details>

<details>
<summary><strong>Terminal Control Room (TUI)</strong> — ship status, activity log, market, and haul session, with TTS callouts.</summary>

- Live panels: SHIP STATUS (commander, system, station, fuel, cargo, FSD target), ACTIVITY log, and MARKET table from `Market.json`.
- Full command bar for `dock`, `undock`, `jump`, `buy`, `sell`, `dest`, `home`, `travel`, `market ...`.
- Start haul work from the command bar: `haul [commodity]`, `haul start`, `haul load`, `haul search [system]`, `haul search url <inara-url>`, `haul route <n>`, `multi_leg_haul <route>`.
- `stats [today|48h|week|month|all|since YYYY-MM-DD]` summarises saved haul runs: total profit, profit per hour, time, and per-route and per-commodity totals.
- `reload_config` and `reload_keymap` reread `config.toml` and the bindings file without a restart.
- `pause` / `resume` an active two-way haul. Session stats (timer, profit, runs, average run time) cover one haul: they stay on screen after it stops and start from zero on the next haul; `new_session` zeroes them mid-haul.
- `Ctrl-R` reopens replay / command history; `Ctrl-C` interrupts (haul-aware safe stop first, cancel on second).
- Speaks TTS callouts locally, e.g. "commander, ship ready to jump" at the end of a leg.

<img src="docs/assets/tui-control-room.png" alt="Terminal Control Room TUI" width="50%">
</details>

## Quick Start

```sh
uv sync
uv run python3 tools/setup_piper.py   # optional: set up Piper TTS, see Piper Voice below for more details
uv run python3 control_room.py lan
```

`lan` starts a headless server and prints the bound URL on startup (e.g. `http://192.168.1.50:8765`). Open that URL in a browser to use the web frontend — ideally on a **secondary device** (tablet, phone, or another laptop) so Elite can stay the foreground application on the game machine. Routines drive Elite by key input, and alt-tabbing away from the game window will break them.

Live-validated on **macOS** (Elite through CrossOver), **Windows** (community-validated) and the **Steam Deck** (Elite under Proton, Desktop and Game Mode).

**Before your first run:** set arrow-key secondaries on `UI_Up / UI_Down / UI_Left / UI_Right` in Elite. See [docs/user/bindings-setup.md](docs/user/bindings-setup.md).

Full walkthrough: [docs/user/getting-started.md](docs/user/getting-started.md).

## Hub: Connected Intelligence

Play on more than one machine (a desktop, a second PC, a Steam Deck)? Make one the **hub** and the others **peers**:

```sh
uv run python3 control_room.py hub    # on the hub
uv run python3 control_room.py peer   # on every other machine
```

Peers find the hub on the LAN, keep a link open to it and send up every market, station fact and finished haul run (queued while the hub is away, so nothing is lost). Open only the hub's pages: pick a machine in the sidebar's node picker to see and drive it, read one market database and one haul history for all of them, and play any machine's callouts on the hub or in your browser, with that machine muted.

Commands go the other way too: from the hub's pages, the haul page, Controls, Travel and the command box run on the picked peer, and `POST /api/command?node=<node_id>` sends a command to it from a script ([command-api.md](docs/user/command-api.md)).

Tokens, names, a fixed hub address and the role table: [docs/user/hub.md](docs/user/hub.md).

## Steam Deck

Everything lives in your home folder, so it survives SteamOS updates. No `sudo` and no `config.toml`: journal and bindings paths are found in the Proton prefix, and keys go through a `/dev/uinput` virtual keyboard the `deck` user can already open.

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/TheClooneyCollection/EDControlRoom.git ~/EDControlRoom
cd ~/EDControlRoom
~/.local/bin/uv sync
~/.local/bin/uv run python3 tools/deck_keymap.py           # show the keyboard keys it would add
~/.local/bin/uv run python3 tools/deck_keymap.py --write   # with Elite closed
~/.local/bin/uv run python3 control_room.py lan
```

The Deck's controller preset leaves most actions off the keyboard; `tools/deck_keymap.py` adds the keys routines press without touching your controller bindings. Details: [docs/user/install.md](docs/user/install.md#steam-deck--linux).

## Piper Voice

Callouts use the system voice by default (`say` on macOS, `spd-say` / `espeak-ng` on Linux, Windows speech). For a more natural voice, install [Piper](https://github.com/OHF-Voice/piper1-gpl) with one command:

```sh
uv run python3 tools/setup_piper.py                 # Cori (en_GB, high quality), ~115 MB
uv run python3 tools/setup_piper.py --voice jenny   # or Jenny (en_GB, medium quality)
```

It installs `piper-tts` as a `uv` tool, downloads the voice (on macOS into `~/Library/Application Support/EDControlRoom/piper`), writes `[tts.piper]` into `config.toml`, and speaks a test line. Restart `control_room.py` to pick it up. Pace, intonation and volume can be tuned in `[tts.piper]` (see [config.example.toml](config.example.toml)) or live from the `/controls` Voice panel. Delete the `[tts.piper]` section to go back to the system voice.

## Assisted Haul Loop

A co-pilot, not an autopilot. You fly the jumps; the routine takes over the part that lives behind station menus.

When your ship drops near a station, the **two-way haul routine** handles the station cycle end to end: request docking, work through station services, sell, refuel and repair, buy the return cargo, set the next-leg route, undock, clear mass lock, and prime the FSD. When the drive is primed it calls the commander by title or name and announces the ship is ready to jump. That is your cue to take over for alignment and the next jump.

It fits high-volume A↔B cargo work like community goal loops or long chill hauls, where the station cycle is the repetitive part and your attention is better spent flying. Pick the pair from the Routes page, the Markets page's Best deal or an Inara search, and **Open in haul**.

> [!WARNING]
> **The assisted haul loops break the Elite Dangerous Terms of Use.** You still fly the jumps, but at each station the routine does the station work for you from one click: request docking, sell, buy, plot the next leg, undock and prime the FSD. Frontier counts more than one in-game action per button press as automation and does not permit it ([source](https://forums.frontier.co.uk/threads/does-anyone-has-experience-using-tools-called-fleet-carrier-macros.604481/)). **Do not run them on an account you'd mind losing.** No warranty, no assurance of account safety.
>
> Other buttons that send keys to the game are single actions you trigger yourself; judge those for yourself.

**See it in action:** [live stream demo: the co-pilot handling a station cycle](https://www.youtube.com/live/YKbz7xtc22Q?t=6014s)

<a href="https://www.youtube.com/live/YKbz7xtc22Q?t=6014s"><img src="docs/assets/haul-vr.png" alt="Hauling in VR with EDControlRoom's help, click to watch on YouTube" width="50%"></a>

## Documentation

- [docs/user/](docs/user/): install, bindings, getting started, haul workflow, commands, troubleshooting.
- [docs/user/command-api.md](docs/user/command-api.md): run Control Room commands over HTTP (`POST /api/command`) from `curl`, scripts, or Shortcuts.
- [docs/user/background-input.md](docs/user/background-input.md): macOS background input through a helper in the CrossOver bottle (beta: keep the mouse off the game window while routines run). Coding agents can run the setup with the repo's `edcr-background-input` skill (`.agents/skills/`, linked from `.claude/skills/`).
- [docs/operators/](docs/operators/): operator references (control room, remote / multi-client, bindings files, input and market timing).
- [docs/diagnostics/](docs/diagnostics/): CLI and bindings reference for diagnostics.
- [docs/status/README.md](docs/status/README.md): maintained project status entrypoint.

## Development

Use the repo `uv` environment for tests:

```sh
uv run python3 -m unittest discover -s tests
```

`main` is the active rolling-update branch; stable features and releases are marked with semantic version tags (`vX.Y.Z`). Commits use Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`, `chore:`).

## Repo Layout

- `control_room.py`: primary operator surface at the repo root.
- `tools/`: supported auxiliary CLIs (`run_routine.py`, `diagnostics.py`, `ship_controls.py`, bindings helpers).
- `edap/`: active runtime code.
- `web/`: the web frontend pages (`/haul`, `/markets`, `/routes`, `/controls`, `/travel`, `/multi-haul`).
- `tools/scratch/`: exploratory probes and one-off validation helpers.

## Contributing

Issues and PRs welcome. Before opening a PR:

- Follow Conventional Commits for commit messages.
- Run the test suite: `uv run python3 -m unittest discover -s tests`.
- If your change touches user-visible behavior, update the relevant doc under [docs/user/](docs/user/) or [docs/operators/](docs/operators/).

Bug reports and feature ideas are best filed as GitHub issues with journal / config details when relevant. Chat and questions: [Discord](https://discord.gg/73YSUBhfRG).

## License

MIT. See [LICENSE](LICENSE). This project traces back to the original ED autopilot work by SKai2 and is being maintained and reshaped for the macOS-first Control Room direction.
