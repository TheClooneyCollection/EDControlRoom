# Control Room Command Reference

Every command you can type in the TUI or web command bar. For the haul flow specifically, see [haul-workflow.md](haul-workflow.md).

## Contents

- [Movement and Routing](#movement-and-routing)
- [Cargo](#cargo)
- [Haul](#haul)
- [Market](#market)
- [Session](#session)
- [Key Bindings in the TUI](#key-bindings-in-the-tui)
- [Panels](#panels)
- [Files EDControlRoom Writes](#files-edcontrolroom-writes)

## Movement and Routing

- `dock`
- `undock`
- `jump`
- `dest <system>` — set destination via the galaxy map
- `set_dest <system>` — explicit form
- `home` — route to the saved home system
- `home set <system>` — save a home system
- `home set` — save the current system

## Cargo

- `buy <item> [N|max]`
- `sell`
- `sell <item> [N|max]`

`sell` with no explicit item falls back to `Cargo.json` if the in-memory cargo manifest is empty.

## Haul

- `haul [commodity]` — the two-way haul loop.
- `haul load [path]` — load `haul.toml` from the repo root by default, or a custom path.
- `haul search home` — search Inara using the saved home system as origin.
- `multi_leg_haul <route.json | spansh-url>` (alias `mult`) — finite multi-leg route.

## Market

- `market` — show the market panel.
- `market filter <name>` — filter to a commodity.
- `market clear` — clear the filter.
- `market lock` / `market unlock` — hold or release the current view.

## Session

- `replay` (or `Ctrl-R`) — recent-command history with prefix filter.
- `commands` — list commands.
- `help [command]` — inline help.
- `instant`, `instant on`, `instant off` — toggle the 5-second safety delay for future commands.
- `q`, `quit`, `exit`.

## Key Bindings in the TUI

- `Ctrl-R` — open replay / history.
- `Ctrl-C` / `Ctrl-D` when idle — exit. During `haul`, first press queues a safe stop at the next station-1 boundary, second press cancels immediately.

## Panels

The TUI shows three panels driven by journal + status files:

- **SHIP STATUS**: commander, system, station, flight state, fuel, credits, cargo, `Destination` from `Status.json`, and journal FSD target.
- **ACTIVITY**: live event log and routine progress lines. Startup writes version info here; if update checks are enabled, so do release notifications.
- **MARKET**: commodity table from `Market.json` with filter and lock/unlock.

The web frontend shows the equivalent state plus the haul search and Spansh route panels described in [getting-started.md](getting-started.md).

## Files EDControlRoom Writes

- `.control_room_state.json` — cross-session command history and one saved default haul profile.
- `artifacts/control-room.log` — mirror of consumed journal events.
