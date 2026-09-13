# Getting Started

This is the recommended way to run EDControlRoom day to day: one process serves the runtime, you keep the terminal TUI open for TTS callouts, and you drive it from your browser.

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

Fill in the origin (and optionally destination), max route distance, cargo capacity, min supply / demand, then **Search routes**. Click a result and use **Set destination** or **Start route** to dispatch it. Land settlements are excluded for now; only station and carrier routes are returned.

### Spansh Route Fetch and Comparison

The route comparison panel fetches a Spansh route between two systems and lays it out beside the in-game route.

![Spansh route fetch and comparison](../assets/spansh-routes.png)

From, jump range, and supercharge mode auto-fill from live ship state (current system + Loadout event). Set To, adjust efficiency and any other fields, and optionally a final station. **Fetch Spansh**, **Compare**, or **All in one** to run the full flow, then **Switch to Spansh** to start the Spansh route runner — it flies the route waypoint by waypoint and auto-sets the galaxy map for the next waypoint every time you arrive.

## Attach a TUI for TTS

`lan` is headless, so it does not speak TTS on its own. Open a TUI client in a separate terminal to get the "commander, ship ready to jump" callouts and a live activity log. Paste the URL `lan` printed, or use the shorter `host:port` form:

```sh
uv run python3 control_room.py connect http://<ip>:8765/ --token edcr
uv run python3 control_room.py connect <ip>:8765 --token edcr
```

Swap `edcr` for your token if you overrode it. TTS is client-local; the browser will not speak.

Typical setup: one machine runs `control_room.py lan`, a second terminal (same machine or a second monitor / LAN box) runs `connect ...` for TTS + activity log, iPad or another window drives the browser UI.

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
