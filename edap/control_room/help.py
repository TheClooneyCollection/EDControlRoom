from __future__ import annotations

from edap.control_room.models import CommandHelp


CONTROL_ROOM_COMMANDS: list[CommandHelp] = [
    CommandHelp(
        name="dock",
        usage="dock",
        summary="Dock at the current station target and auto-refuel plus auto-repair after touchdown.",
        detail="Starts the docking routine. If you're already in normal space it skips the supercruise-exit wait; otherwise it waits for the drop, sends the docking request menu flow, then auto-refuels and attempts one repair press after docking before returning to station services. Prefix the command with ! to bypass the configured control-room start delay for that launch only.",
    ),
    CommandHelp(
        name="undock",
        usage="undock",
        summary="Launch from the current station and wait until the ship is clear of the station.",
        detail="Runs the station launch menu flow, waits for the Undocked journal event, then waits for the NoTrack music event that confirms the ship has cleared the station before reporting success.",
    ),
    CommandHelp(
        name="jump",
        usage="jump",
        summary="Trigger the FSD jump sequence and zero throttle on arrival.",
        detail="Sends the hyperspace control, waits for the jump to start, waits to re-enter supercruise at the destination, then sets speed to zero.",
    ),
    CommandHelp(
        name="escape",
        usage="escape",
        summary="Set speed full and boost away until the FSD mass-lock clears.",
        detail="Sets throttle to 100%, then checks Status.json in a loop: if the FSD mass-locked flag is set, fires a boost and waits the configured boost delay before checking again. Stops and reports success once the flag clears or is absent.",
    ),
    CommandHelp(
        name="boost",
        usage="boost",
        summary="Fire boost three times immediately.",
        detail="Sends the ship's boost binding three times in a row without checking mass-lock state. Use escape instead when you want the Status.json mass-lock check loop.",
    ),
    CommandHelp(
        name="buy",
        usage="buy <item> [amount|max]",
        summary="Buy a commodity from the current station market.",
        detail="Opens the commodities market, finds the named item in the buy list, sets the requested quantity or MAX, confirms the trade, and waits for a MarketBuy journal event.",
    ),
    CommandHelp(
        name="sell",
        usage="sell [item] [amount|max]",
        summary="Sell cargo from the current station market.",
        detail="With an item name it sells that commodity. With no item it walks your cargo manifest and tries to sell every non-stolen, non-mission cargo item, skipping items the market won't buy.",
    ),
    CommandHelp(
        name="haul",
        usage="haul [commodity] | haul load [path] | haul search [system] | haul search url <inara-url> | haul route <n>",
        summary="Run the two-station haul loop, load a saved haul profile, or fetch live Inara trade routes.",
        detail="Starts a two-station loop: each station sells the other station's outbound cargo if present, then buys its own outbound cargo if configured. Plain `haul` still prompts for both station names, both systems, both outbound cargo names, the galaxy-map settle delay, and the docking timeout. `haul load` reads `haul.toml` by default, or a supplied TOML path, then launches the same routine with those values. `haul search [system]` opens one editable all-parameters-at-once Inara search line seeded from ignored local `haul_search.toml`, the current ship system, and current ship cargo capacity; `haul search home` uses the saved `control_room.home_system`. `haul search url <inara-url>` skips the prompt and runs the pasted Inara query directly. When results load, the haul route picker opens so Enter can load the highlighted route into the haul prompt, `d` can set `dest` to the highlighted route's first-system entry, and Esc can dismiss it; `haul route <n>` still loads one shown result directly with station and commodity defaults prefilled. At least one station buy commodity is required for the loop mode.",
    ),
    CommandHelp(
        name="multi_leg_haul",
        usage="multi_leg_haul <route.json | spansh-url>",
        summary="Run a standalone multi-leg haul route from our JSON schema or a Spansh result.",
        detail="Loads a generalized multi-leg haul definition, then resumes from live journal/cargo/market state rather than persisted session state. Use this for finite multi-hop trading routes that buy and sell the exact commodity list on each leg.",
        aliases=("mult",),
    ),
    CommandHelp(
        name="dest",
        usage="dest <system> | dest home",
        summary="Open the galaxy map and plot a route to a named system.",
        detail="Opens the galaxy map, types the destination into search, plots the route, verifies NavRoute.json, and closes the map again. Use `dest home` to route to the saved `control_room.home_system`. Control room also prompts for the galaxy-map settle delay, with Enter accepting the configured default.",
        aliases=("set_dest",),
    ),
    CommandHelp(
        name="home",
        usage="home | home set <system>",
        summary="Route to your saved home system, or update that saved home system in config.",
        detail="Plain `home` behaves like `dest <home system>` using `control_room.home_system` from config. `home set <system>` writes that setting into the active config file, and bare `home set` falls back to the current ship system when control room already knows it. When control room started from the default example fallback, the setter creates repo-root `config.toml` instead of editing `config.example.toml`.",
    ),
    CommandHelp(
        name="market",
        usage="market | market clear | market filter <name> | market lock | market unlock",
        summary="Control the market panel filter and lock state.",
        detail="Use 'market filter <name>' to filter visible items, 'market' or 'market clear' to remove the filter, 'market lock' to pin the panel to the currently displayed market while updates for that same market continue flowing in, and 'market unlock' to resume following the latest loaded market.",
    ),
    CommandHelp(
        name="verbose",
        usage="verbose [on|off]",
        summary="Turn verbose keypress logging on or off.",
        detail="When verbose mode is on, individual key presses from routine dispatch are written into the activity log. When off, only higher-level progress messages are shown.",
    ),
    CommandHelp(
        name="instant",
        usage="instant [on|off]",
        summary="Toggle the control-room command launch delay off or on.",
        detail="With no argument it toggles instant mode. When instant mode is on, executable commands launch immediately without the configured control-room start delay until you turn it off again. The ! prefix still works for one-off immediate launches.",
    ),
    CommandHelp(
        name="pause",
        usage="pause",
        summary="Pause an active two-way haul at the next station boundary.",
        detail="Requests a pause for the running two-way haul. The routine finishes the current transit or station sell step, pauses before the next station buy/departure at either configured station, and freezes haul session/current-run timers until `resume` is issued.",
    ),
    CommandHelp(
        name="resume",
        usage="resume",
        summary="Resume a two-way haul paused at a station.",
        detail="Releases a paused two-way haul so it continues from the station boundary where it stopped. If a pause was requested but the ship has not reached the next station yet, this cancels the pending pause request.",
    ),
    CommandHelp(
        name="new_session",
        usage="new_session",
        summary="Clear persisted haul session time and profit, then start a fresh session now.",
        detail="Resets the haul session totals that survive control-room restarts, including session profit, session duration, completed-run totals, and last-run summary fields. If a haul is active, the routine keeps running and the session counters restart from the moment you issue the command.",
        aliases=("clear",),
    ),
    CommandHelp(
        name="stop",
        usage="stop",
        summary="Freeze persisted haul session time and profit without clearing totals.",
        detail="Stops the persisted haul session clock so relaunches and idle time do not keep extending the current session. The saved totals remain visible, and the next haul resumes from those totals without counting the stopped downtime. This command refuses to run while a haul routine is still active.",
    ),
    CommandHelp(
        name="set_pid",
        usage="set_pid [pid|process-name|foreground]",
        summary="Keep using the foreground app, or target a specific process id for input dispatch.",
        detail="With no argument, control room tries to find `EliteDangerous64.exe` automatically and targets that pid. `set_pid <number>` stores an explicit pid. `set_pid <process-name>` auto-detects by executable name. `set_pid foreground` clears any pid or hwnd target and returns to normal foreground input.",
    ),
    CommandHelp(
        name="set_hwnd",
        usage="set_hwnd [hwnd|process-name|foreground]",
        summary="On Windows, target a specific top-level game window handle for input dispatch.",
        detail="With no argument, control room tries to find the main window for `EliteDangerous64.exe` automatically. `set_hwnd <number>` stores an explicit hwnd, and hex forms like `0x123456` are accepted. `set_hwnd <process-name>` auto-detects by executable name. `set_hwnd foreground` clears any pid or hwnd target and returns to normal foreground input. On macOS this command reports that hwnd targeting is unsupported.",
    ),
    CommandHelp(
        name="commands",
        usage="commands",
        summary="List every supported control-room command.",
        detail="Prints the command names and their one-line summaries so you can discover what control room currently supports.",
    ),
    CommandHelp(
        name="help",
        usage="help [command]",
        summary="Show general help or explain one command in plain English.",
        detail="With no argument it explains how to discover commands. With a command name, it prints that command's usage, aliases, and what it is meant to do in human terms.",
        aliases=("?",),
    ),
    CommandHelp(
        name="replay",
        usage="replay",
        summary="Open the replay history browser for execute-or-edit replay.",
        detail="Shows recent saved commands across sessions in the activity-pane replay browser. Press Enter to execute the selected entry with its normal delay behavior, press ! to execute it immediately without adding a ! to the saved command, press e to reopen it for editing, or press * on a haul entry to save or clear it as the default haul setup.",
        aliases=("history",),
    ),
    CommandHelp(
        name="quit",
        usage="q | quit | exit",
        summary="Cancel active work if needed, then shut down control room cleanly.",
        detail="Starts the control-room shutdown path. If a routine is running, control room cancels it first and exits after the worker unwinds; otherwise it exits immediately.",
        aliases=("q", "exit"),
    ),
]

CONTROL_ROOM_COMMAND_INDEX: dict[str, CommandHelp] = {}
for command in CONTROL_ROOM_COMMANDS:
    CONTROL_ROOM_COMMAND_INDEX[command.name] = command
    for alias in command.aliases:
        CONTROL_ROOM_COMMAND_INDEX[alias] = command
