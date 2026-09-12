# Control Room (Operator Reference)

`control_room.py` is the main live operator surface. For the recommended day-to-day setup (TUI + web frontend on the LAN), see [../user/getting-started.md](../user/getting-started.md). For the haul workflow, see [../user/haul-workflow.md](../user/haul-workflow.md). For the full command list, see [../user/commands-reference.md](../user/commands-reference.md).

This page is the operator-reference view: run modes, panels, and the specifics of how Control Room behaves in a live session.

## Run Modes

```sh
uv run python3 control_room.py                         # embedded local TUI only
uv run python3 control_room.py --market aluminium      # embedded local, pre-focused market
uv run python3 control_room.py local                   # server bound to 127.0.0.1
uv run python3 control_room.py lan                     # server bound to detected LAN IPv4 (recommended)
uv run python3 control_room.py serve --host 0.0.0.0 --port 8765
uv run python3 control_room.py connect 192.168.1.50:8765 --token edcr
```

`lan` autodetects a non-loopback IPv4, preferring RFC1918 addresses and skipping VPN-owned ranges like `198.18/15` (Cloudflare WARP) and `100.64/10` (CGNAT). Use `--host` for an explicit bind, `0.0.0.0` for all interfaces.

Access token defaults to `edcr` when `--token` is omitted; the built-in web page auto-fills the same default. Override on both ends if you want a different token. The TUI `connect` client requires an explicit `--token`.

If `config.toml` exists in the repo root, EDControlRoom loads it automatically.

For multi-client / operator-vs-observer semantics, see [control-room-remote.md](control-room-remote.md).

## Panels

- `SHIP STATUS`: commander, system, station, flight state, fuel, credits, cargo, `Destination` from `Status.json` (`system/body/name`), and journal FSD target.
- `ACTIVITY`: live event log and routine progress lines. Startup writes version info; if update checks are enabled, so do release notifications.
- `MARKET`: commodity table from `Market.json` with filter and lock/unlock.

## Ship-Affecting Delay

Commands that press keys into Elite wait `5` seconds before the first press so you can focus the game window. `instant`, `instant on`, `instant off` toggle that delay for future commands. Useful when you are remoted in and do not need the pause.

## Haul Behavior

For the workflow story, see [../user/haul-workflow.md](../user/haul-workflow.md). Behavior specifics:

- `haul [commodity]` runs the two-way loop used by `tools/run_routine.py --routine haul_loop`.
- `haul load [path]` loads repo-root `haul.toml` by default.
- Resume is journal + sidecar based; no clean-state assumption.
- One default haul setup persists across restarts.
- `replay` / `Ctrl-R` relaunches recent haul commands.
- Interrupt: first `Ctrl-C` / `Ctrl-D` queues a stop at the next station-1 boundary after the return sale; second cancels immediately.

## Multi-Leg Haul

`multi_leg_haul <route.json | spansh-url>` (alias `mult`) runs a standalone finite multi-leg route. Route input can come from the normalized JSON at `docs/schemas/multi_leg_haul.schema.json` (see `templates/multi_leg_haul.example.json`) or from a Spansh trade-result URL / payload. Resume state is re-derived from journal, `Cargo.json`, `Market.json`, and the route definition. The public schema intentionally excludes plan / execution state.

## Persistence

- `.control_room_state.json`: cross-session command history and the saved default haul profile.
- `artifacts/control-room.log`: mirror of consumed journal events.

## Related

- [../user/commands-reference.md](../user/commands-reference.md)
- [bindings-files.md](bindings-files.md)
- [input-timing.md](input-timing.md)
- [market-timing.md](market-timing.md)
- [manual-journal-routine-testing.md](manual-journal-routine-testing.md)
- [control-room-remote.md](control-room-remote.md)
