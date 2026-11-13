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
- In Near, the range is also how far the first station may be from you: with **1 jump** or **2 jumps** a short route 50 Ly away is left out. Use **4 jumps**, **100 Ly** or **Global** to see it.
- Each station's title line shows how many Ly away it is from your current system (or the system you type), when that system has coordinates in the database; the **Jumps** column shows the Ly between the two stations.
- The **Out** and **Back** columns show each leg on three lines: the commodity; its buy price at the loading station, sell price at the other one, the margin per ton and the tons in a full hold, e.g. `3,420 → 40,684 (+37,264/t) × 720 t`; then supply at the loading station and demand at the other, e.g. `Sup 14,595 · Dem 2,310`. `/haul` route rows show the same three lines per leg in the Cargo column, without the tons.
- **1 / 2 / 4 jumps** size the range by your laden jump range; **100 / 250 Ly** use a flat distance.
- Filters: cargo, min supply, max station distance (Ls), max data age, surface stations, fleet carriers. Empty fields fall back to `haul_search.toml` and your current ship.
- Fleet carriers show their display name with the callsign, e.g. `GRAND ARTS THEATRE (JFF-15Z)`. The title line says `open` or `closed`; the line below says who a closed carrier docks (squadron, friends, both or nobody), or `access unknown` when no EDDN upload has reported it yet. With fleet carriers on, **Open to all only** (on by default) hides carriers known to dock only their squadron or friends; carriers of unknown access stay.
- Carriers that have moved on are hidden: one whose signal was seen in another system after its market was read, one a `CarrierJump` put elsewhere, or one missing from the carrier list your own journal wrote for its system later. The game writes that list once per visit, at login or your first drop from supercruise there, so jumping through a system in supercruise does not check it.
- Demand is not filtered: a station buys anything it lists a sell price for, even with a tiny demand (for example a station that also produces it).
- Routes are ranked by profit per hour. The trip time is an estimate fitted from real haul runs: jumps, supercruise distance and time docked.
- Profit per trip should match Inara's for the same hold. Profit per hour usually comes out lower than Inara's, because this trip time is more cautious (for example 930 s where Inara implies about 770 s). It was fitted on real runs, so trust it over Inara's.
- **Copy** puts the route on the clipboard as JSON; paste it into the **Copy / paste route** box on the haul page to run it. Routes with a commodity whose in-game name is not known yet show "name unknown" instead; visiting a market that sells it teaches the name.

Prices are only as fresh as the last commander who docked there; the **Data age** column shows how old each route's prices are.

The haul page and the Markets page show fleet carriers the same way, `NAME (CALLSIGN)`, once the market database has seen the carrier's name; until then they show the callsign.

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

[eddn.time_model]        # trip time for profit per hour; set only what you change
source = "config"        # "fitted": fit them per ship from the journal events instead
fit_days = 14.0          # days of journal events the fit reads
docked_s = 90.0          # trading while docked, per station
travel_base_s = 110.0    # undock, leave the station, dock again
first_jump_s = 170.0     # charge, align and the first jump
per_extra_jump_s = 65.0  # each further jump
supercruise_coeff = 13.0 # supercruise seconds = coeff * Ls^(1/3)
unknown_dist_ls = 1000.0 # Ls assumed when a station's distance is unknown
surface_extra_s = 30.0   # planetary approach and landing
```

Restart the server after editing these by hand, or use the Config page below.

With `source = "fitted"` the hub (or a standalone server) fits the values to how you actually fly, from the journal events of every node over the last `fit_days`: per ship once it has 30 clean Undocked-to-Docked legs, else every ship pooled, else the configured values. A field with fewer than 10 legs that tell it apart (for example two-jump legs for `per_extra_jump_s`) keeps the configured value. A peer uses its hub's settings and fit for its own ship. The **Config** page (`/config`) shows both sets side by side with the legs behind each fitted value; edit the configured values, pick **Configured** or **Fitted** and press **Save**. It writes `[eddn.time_model]` in `config.toml` and applies at once, no restart. On a peer the page shows the hub's settings read-only; change them on the hub. `/routes` and Best deal say which set the trip time came from.

On a second machine you can skip the listener and ask a home Control Room instead: see [hub.md](hub.md).

`tools/eddn_listen.py` runs the same listener on its own, without the server. Do not run it while the server is listening: both would write the same database.
