# Trade Routes (EDDN)

The web **Routes** page (`/routes`) finds two-way trade routes from live market prices, without Inara.

## Where the prices come from

A standalone or hub Control Room always keeps a local SQLite market database, `.eddn_markets.sqlite3` in the repo folder (about 3.5 KB per market); a peer keeps none and asks the hub. Your own visited markets and the systems and stations in your journal always go into it. With `[eddn]` on, the `lan` server also listens to [EDDN](https://github.com/EDCD/EDDN), the feed other commanders' tools upload market data to, and every market update goes into the same file. Markets not updated for 7 days are dropped.

The EDDN listener is off by default; turn it on with `enabled = true` under `[eddn]` (see Settings below). The database starts empty, so give it a while: after an hour or so the busy parts of the bubble are covered, and coverage keeps growing while the server runs.

## Checking it works

- The server log prints an EDDN status line every 30 seconds:
  `EDDN connected: 5210 msgs, 830 market updates, 0 errors | db 553 markets, 41000 prices, ...`
- "EDDN relay silent; reconnecting." now and then is normal; the listener reconnects by itself.
- On `/routes`, the **EDDN** chip in the top bar shows the market count, and the **EDDN listener** panel adds a line every 10 seconds with what arrived since the last check.

## Using the Routes page

- **Near** shows routes whose first station is within range of your current system (or the system you type). **Global** searches every market in the database.
- **1 / 2 / 4 jumps** size the range by your laden jump range; **100 / 250 Ly** use a flat distance.
- Filters: cargo, min supply, max station distance (Ls), max data age, surface stations, fleet carriers. Empty fields fall back to `haul_search.toml` and your current ship.
- Demand is not filtered: a station buys anything it lists a sell price for, even with a tiny demand (for example a station that also produces it).
- Routes are ranked by profit per hour. The trip time is an estimate fitted from real haul runs: jumps, supercruise distance and time docked.
- **Copy** puts the route on the clipboard as JSON; paste it into the **Copy / paste route** box on the haul page to run it. Routes with a commodity whose in-game name is not known yet show "name unknown" instead; visiting a market that sells it teaches the name.

Prices are only as fresh as the last commander who docked there; the **Data age** column shows how old each route's prices are.

## Best deal on the Markets page

The **Best deal** panel on `/markets` compares two stations whose market you opened and shows the numbers Inara's trade route view shows:

- **Profit per ton**: both legs added (Cr/t).
- **Profit per trip**: a full-hold round trip, the hold capped by the seller's stock.
- **Profit per hour**: profit per trip over the estimated round-trip time, from the same time model as the Routes page, with the trip time, jumps and distance under it. Empty **Laden jump range** uses your ship's laden range, worked out from its journal `Loadout` (full hold and full tank, shown as `<value> (ship)`); before a Loadout is seen it falls back to `haul_search.toml` as on the Routes page.
- **Measured per hour**: profit per hour of your completed haul runs between the two stations, either direction, flown in the ship you are in now, over the window picked next to it (48h, 7 days by default, 30 days or all; the page remembers your pick). It shows the run count, the average loop time and the laden jump range the newest of those runs was flown at, with your ship's range today beside it when that differs, so a ship that now jumps further shows. Each run records its ship (ship ID, type, name, ident, cargo capacity, max and laden jump range); runs from before ship tracking count within the window and are counted as "ship unknown". On a hub it counts every node's runs (the hub's own and every peer's); a peer asks the hub, and says so when the hub is away.

The estimate needs each system's coordinates and each station's distance from the star and type. They come from the market database (EDDN messages, your journal: a station you docked at, a system you jumped to, and your Market.json station types; newest wins), then from the [Ardent Insight](https://ardent-insight.com) API for what is still missing. Ardent answers are kept in the same database, which helps the Routes page too. On a peer the panel shows "-" and says the hub supplies station facts. If Ardent is slow or down (3 second limit, tried again after 10 minutes) or one is still unknown, the panel shows "-" and names what is missing; it never guesses.

## Settings

In `config.toml`:

```toml
[eddn]
enabled = true           # off by default
database_file = ".eddn_markets.sqlite3"
max_age_days = 7.0       # drop markets older than this
status_every_s = 30.0    # server log status line; 0 turns it off
```

Restart the server after changing these.

On a second machine you can skip the listener and ask a home Control Room instead: see [hub.md](hub.md).

`tools/eddn_listen.py` runs the same listener on its own, without the server. Do not run it while the server is listening: both would write the same database.
