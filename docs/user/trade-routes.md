# Trade Routes (EDDN)

The web **Routes** page (`/routes`) finds two-way trade routes from live market prices, without Inara.

## Where the prices come from

The `lan` server listens to [EDDN](https://github.com/EDCD/EDDN), the feed other commanders' tools upload market data to. Every market update goes into a local SQLite file, `.eddn_markets.sqlite3` in the repo folder (about 3.5 KB per market). Markets not updated for 7 days are dropped.

This is on by default. The database starts empty, so give it a while: after an hour or so the busy parts of the bubble are covered, and coverage keeps growing while the server runs.

## Checking it works

- The server log prints an EDDN status line every 30 seconds:
  `EDDN connected: 5210 msgs, 830 market updates, 0 errors | db 553 markets, 41000 prices, ...`
- "EDDN relay silent; reconnecting." now and then is normal; the listener reconnects by itself.
- On `/routes`, the **EDDN** chip in the top bar shows the market count, and the **EDDN listener** panel adds a line every 10 seconds with what arrived since the last check.

## Using the Routes page

- **Near** shows routes whose first station is within range of your current system (or the system you type). **Global** searches every market in the database.
- **1 / 2 / 4 jumps** size the range by your laden jump range; **100 / 250 Ly** use a flat distance.
- Filters: cargo, min supply / demand, max station distance (Ls), max data age, surface stations, fleet carriers. Empty fields fall back to `haul_search.toml` and your current ship.
- Routes are ranked by profit per hour. The trip time is an estimate fitted from real haul runs: jumps, supercruise distance and time docked.
- **Copy** puts the route on the clipboard as JSON; paste it into the **Copy / paste route** box on the haul page to run it. Routes with a commodity whose in-game name is not known yet show "name unknown" instead; visiting a market that sells it teaches the name.

Prices are only as fresh as the last commander who docked there; the **Data age** column shows how old each route's prices are.

## Settings

In `config.toml`:

```toml
[eddn]
enabled = false          # turn the listener off
database_file = ".eddn_markets.sqlite3"
max_age_days = 7.0       # drop markets older than this
status_every_s = 30.0    # server log status line; 0 turns it off
```

Restart the server after changing these.

`tools/eddn_listen.py` runs the same listener on its own, without the server. Do not run it while the server is listening: both would write the same database.
