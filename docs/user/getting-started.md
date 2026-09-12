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

Uvicorn logs the bound URL as it starts, something like:

```
Uvicorn running on http://192.168.1.50:8765
```

That address is the web frontend. The Textual TUI stays running in this terminal window and handles TTS callouts.

**Token.** With no `--token`, both the server and the built-in web page default to `edcr`, so the browser connects without you typing anything. Pass `--token <your-token>` on both ends if you want a different one.

## Open the Web Frontend

On any device on the same LAN, open the URL from the startup log in a browser (or `http://localhost:8765` from the same machine). This is the main operator surface.

![Web quick stats](../assets/quick-stats.png)

Top of the page is the two-way haul dashboard: home / current system, destination, cargo, session profit, and the five stages of the active haul routine (Buy, Undock, Depart, Transit, Sell). Header controls let you pause / resume / stop the routine and toggle the pre-command safety delay (**Instant off**).

### Web Haul Search

The `/haul` view searches Inara for profitable station-to-station routes near your origin and lets you dispatch one straight into the two-way haul routine.

![Haul search](../assets/haul-search.png)

Fill in the origin (and optionally destination), max route distance, cargo capacity, min supply / demand, then **Search routes**. Click a result and use **Set destination** or **Start route** to dispatch it. Land settlements are excluded for now; only station and carrier routes are returned.

### Spansh Route Fetch and Comparison

The route comparison panel fetches a Spansh route between two systems and lays it out beside the in-game route.

![Spansh route fetch and comparison](../assets/spansh-routes.png)

Set From / To, jump range, efficiency, supercharge state, and (optionally) a final station. **Fetch Spansh**, **Compare**, or **All in one** to run the full flow, then **Switch to Spansh** to hand the route to the active haul.

## Use the TUI for TTS

Keep the terminal window that launched `lan` visible. It runs the TUI and speaks TTS callouts locally, such as the "commander, ship ready to jump" handoff at the end of a haul leg. TTS is client-local; the browser will not speak.

Typical setup: laptop or workstation runs `control_room.py lan` with the terminal on a second monitor for TTS + activity log, iPad or another window drives the browser UI.

### Attach Another TUI

To open a second TUI against the running server (same machine or another LAN box), in a separate terminal run:

```sh
uv run python3 control_room.py connect <ip>:8765 --token edcr
```

Use the IP printed by `lan` on startup, and swap `edcr` for your token if you overrode it. This is useful for a second monitor with TTS on a different machine, or to reattach a TUI after closing the original terminal window.

## The Five-Second Safety Delay

Ship-affecting commands wait **5 seconds** before pressing any keys, so you have time to click back into Elite. Do that as soon as you fire a command from the browser or TUI.

If you are already remote and do not need the pause, type `instant` in the TUI command bar to toggle it off. `instant on` and `instant off` are explicit forms.

## First Haul

1. In Elite, drop near a station you want to buy from.
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
