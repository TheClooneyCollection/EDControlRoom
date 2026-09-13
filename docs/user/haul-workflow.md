# Haul Workflow

`haul` is the strongest end-to-end routine and the clearest example of what EDControlRoom is for. It handles the boring station-side loop so you can stay focused on the parts that still benefit from a human pilot.

## What Haul Does

`haul` can be started from anywhere in the loop — whether you're docked, in supercruise near a station, mid-transit between systems, or just launched. It reads the journal, `Cargo.json`, and `Market.json` to figure out which phase you're in and picks up from there. Starting from the TUI or the web frontend behaves the same way.

At each phase, `haul` walks the ship through:

1. request docking
2. work through station services
3. buy or sell cargo
4. refuel and repair
5. set the route for the next leg
6. leave the station
7. clear mass lock and prime the FSD

There is no auto-align. When the ship is clear and the drive is primed, TTS calls the commander by title or name and says the ship is ready to jump. That is your cue to take over alignment and the next jump.

This makes it directly useful for high-volume A-to-B cargo work such as community goal loops, where the repetitive trading cycle is the part worth automating.

## The Simple Path

From the TUI command bar or the web command bar:

```
haul                 # walks you through an interactive prompt
haul <commodity>     # skips the buy-commodity question
```

Or use the web **Haul search** panel to pick a route from Inara results and click **Start route**. See [getting-started.md](getting-started.md#web-haul-search).

## Reusable Setup: `haul.toml`

If you want the same two-station loop each time without stepping through the prompt, edit a repo-root `haul.toml` (git-ignored) and run:

```
haul load
```

Example `haul.toml`:

```toml
[haul]
galaxy_map_settle = 2.0
dock_timeout = 1200.0

[haul.station_1]
buying = "Aluminium"
name = "Pawelczyk Dock"
system = "Sol"
on_land = false

[haul.station_2]
buying = "Bertrandite"
name = "Trevithick Dock"
system = "Achenar"
on_land = false
```

Notes:

- `buying` is optional on either side, but at least one station must have a buy cargo.
- `on_land = true` hands off after `SupercruiseExit` in the destination system so you can do a surface approach and resume after landing.
- `haul load some-other-file.toml` if you keep multiple named profiles.

## Saved Default

Control Room persists one saved default haul setup across restarts. `replay` or `Ctrl-R` reopens recent commands, including that saved setup.

## Home Routing

Setting a home system gives you one-word routing later.

```
home set <system>    # save a home system
home set             # save the current system if Control Room knows it
home                 # route to the saved home system
dest home            # same, as a dest alias
haul search home     # use home as the Inara search center
```

`home set` updates the active config. If Control Room started from the shipped example fallback (no repo-root `config.toml` yet), it creates a minimal `config.toml` rather than editing the shipped example.

## Resume Semantics

Haul is state-aware. If you cancel or crash mid-run and start it again, it re-derives the current stop and phase from the journal, `Cargo.json`, `Market.json`, and its sidecar state. You do not need to start from a clean station.

## Multi-Leg Haul

For a finite multi-hop route rather than a two-station loop:

```
multi_leg_haul <route.json>
multi_leg_haul <spansh-url>
mult ...                        # short alias
```

The route can come from the normalized JSON schema at `docs/schemas/multi_leg_haul.schema.json` (see `templates/multi_leg_haul.example.json`) or directly from a Spansh trade-result URL / payload. Resume is state-based; rerun and EDControlRoom figures out where you are.

## Interrupt Behavior

- First `Ctrl-C` or `Ctrl-D`: finish the current run, stop at station 1 after the return sale, before the next buy.
- Second `Ctrl-C` or `Ctrl-D`: cancel immediately.

## Related

- [commands-reference.md](commands-reference.md) for every command.
- [../operators/control-room.md](../operators/control-room.md) for the operator-reference view.
- [../operators/market-timing.md](../operators/market-timing.md) if you need to tune the market buy-hold or sell-max timings.
