# Getting Started

This is the recommended way to run EDControlRoom day to day: one process serves the runtime and speaks TTS callouts, and you drive it from your browser.

## Contents

- [Before You Start](#before-you-start)
- [Start Control Room in LAN Mode](#start-control-room-in-lan-mode)
- [Open the Web Frontend](#open-the-web-frontend)
- [TTS callouts and the TUI](#tts-callouts-and-the-tui)
- [The Five-Second Safety Delay](#the-five-second-safety-delay)
- [First Haul](#first-haul)
- [Stopping](#stopping)
- [Where To Go Next](#where-to-go-next)

## Before You Start

- Finished [install.md](install.md).
- Set the arrow-key secondaries described in [bindings-setup.md](bindings-setup.md). This is easy to skip and will silently break galaxy-map automation.
- Elite Dangerous is running.

## Start Control Room in LAN Mode

From the repo root:

```sh
uv run python3 control_room.py lan
```

`lan` starts a headless server. Uvicorn logs the bound URL as it starts, something like:

```
Uvicorn running on http://192.168.1.50:8765
```

That address is the web frontend.

**Token.** With no `--token`, both the server and the built-in web page default to `edcr`, so the browser connects without you typing anything. Pass `--token <your-token>` on both ends if you want a different one.

## Open the Web Frontend

On any device on the same LAN, open the URL from the startup log in a browser (or `http://localhost:8765` from the same machine). This is the main operator surface.

> **Recommended:** open the web frontend on a **secondary device** (second laptop, tablet, phone) rather than the machine running Elite. EDControlRoom drives Elite by sending key input to the game window, so **Elite must be the foreground application** while a routine runs. Alt-tabbing to a browser on the same machine steals focus and breaks the routine. A tablet or second monitor / device sidesteps that entirely.

![Web quick stats](../assets/quick-stats.png)

Top of the page is the two-way haul dashboard: home / current system, destination, cargo, session profit, and the five stages of the active haul routine (Buy, Undock, Depart, Transit, Sell). Header controls let you pause / resume / stop the routine and toggle the pre-command safety delay (**Instant off**).

### Web Haul Search

The `/haul` view searches Inara for profitable station-to-station routes near your origin and lets you dispatch one straight into the two-way haul routine.

![Haul search](../assets/haul-search.png)

Fill in the origin (and optionally destination), max route distance, cargo capacity, min supply / demand, then **Search routes**. Click a result and use **Set destination** or **Start route** to dispatch it. **Surface stations** defaults to No (orbital stations and carriers only); pick "Yes, exclude Odyssey settlements" for planetary ports, or "Yes, with Odyssey settlements" for everything. The docking computer handles planetary ports like orbital ones. Only if you cannot glide close to a station after the drop, turn on its **Manual landing** flag yourself (paste box or `haul.toml`).

**Profit / hr** shows two lines per route: Inara's own figure and trip time, then EDCR's for the ship you fly (or the node picked on a hub), from the same trip time model as the Routes page and Best deal. When EDCR cannot estimate a route it names what it is missing instead.

If a search fails, the results table says why. Inara sometimes asks for an access check, which the background browser cannot pass; the message names the computer that searched (the hub, for a peer) and the command that opens a visible browser there. Pass the check once and search again.

### Spansh Route Fetch and Comparison

The `/travel` page (sidebar **Ship → Travel**, or **More** on phones) fetches a Spansh route between two systems in its Route Comparison panel and lays it out beside the in-game route. The Active route panel above it tracks jumps, LY and boosts remaining while the route runs.

![Spansh route fetch and comparison](../assets/spansh-routes.png)

From, jump range, and supercharge mode auto-fill from live ship state (current system + Loadout event). Set To, adjust efficiency and any other fields, and optionally a final station. **Fetch Spansh**, **Compare**, or **All in one** to run the full flow, then **Switch to Spansh** to start the Spansh route runner — it flies the route waypoint by waypoint and auto-sets the galaxy map for the next waypoint every time you arrive.

## TTS callouts and the TUI

`lan` speaks the "commander, ship ready to jump" callouts on the machine it runs on. Pass `--no-tts` to keep the server silent.

A TUI client adds a live activity log and also speaks every callout on its own machine. If it runs on the same machine as `lan`, start `lan --no-tts` so callouts are not spoken twice. Paste the URL `lan` printed, or use the shorter `host:port` form:

```sh
uv run python3 control_room.py connect http://<ip>:8765/ --token edcr
uv run python3 control_room.py connect <ip>:8765 --token edcr
```

Swap `edcr` for your token if you overrode it.

The haul page can also speak in the browser, for example on an iPhone. Open **Speak announcements on this device** at the bottom of the Active haul routine panel and turn it on. It is per device, so a laptop already running the TUI does not double up. iOS needs one tap on the page after each load, and speech stops when the screen locks.

The server and the TUI use the platform voice (`say`, `spd-say`/`espeak-ng`, or Windows speech) until you set up [Piper](https://github.com/OHF-Voice/piper1-gpl), a natural-sounding local voice. One command installs it on macOS, Linux (including Steam Deck) and Windows:

```sh
uv run python3 tools/setup_piper.py            # Cori, British English, high quality (default)
uv run python3 tools/setup_piper.py --voice jenny   # Jenny (Dioco), British English, medium quality
```

It installs `piper-tts` with `uv tool` (in its own environment, separate from EDControlRoom), downloads the voice into your user data folder and checks it, writes `[tts.piper]` into `config.toml`, and speaks a test line. Rerun it with the other `--voice` to switch voices. Then restart Control Room. Cori is trained on public-domain LibriVox recordings; the Jenny voice is from the [Jenny (Dioco)](https://github.com/dioco-group/jenny-tts-dataset) dataset.

Typical setup: the game machine runs `control_room.py lan` and speaks callouts, and an iPad or another window drives the browser UI. Optionally a second LAN box runs `connect ...` for the activity log.

With more than one machine that plays, make one the hub and the others peers so one set of pages shows and drives all of them: [hub.md](hub.md).

## The Five-Second Safety Delay

Ship-affecting commands wait **5 seconds** before pressing any keys, so you have time to click back into Elite. Do that as soon as you fire a command from the browser or TUI.

If you are already remote and do not need the pause, type `instant` in the TUI command bar to toggle it off. `instant on` and `instant off` are explicit forms.

## First Haul

1. In Elite, dock at a station you want to buy from.
2. In the browser, either search routes (haul search panel) or type `haul <commodity>` in the TUI command bar.
3. Switch to Elite. The routine handles docking, station services, buy, undock, depart, transit, and sell.
4. When the ship is clear and the drive is primed for the next jump, TTS calls out that the ship is ready. Take over for alignment and jump.

For the full workflow, `haul.toml` profiles, and multi-leg routes, see [haul-workflow.md](haul-workflow.md).

## Stopping

- `Ctrl-C` or `Ctrl-D` while `haul` is running: first press queues a safe stop at station 1 after the return sale, second press cancels immediately.
- `q`, `quit`, or `exit` in the TUI when idle.

## Where To Go Next

- [haul-workflow.md](haul-workflow.md): the full haul story.
- [commands-reference.md](commands-reference.md): every Control Room command.
- [troubleshooting.md](troubleshooting.md): when input, journal, or bindings misbehave.
- [../operators/control-room-remote.md](../operators/control-room-remote.md): multi-client / observer semantics if more than one person connects at once.
