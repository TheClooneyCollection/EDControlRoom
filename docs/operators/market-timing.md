# Market Timing

EDControlRoom exposes market quantity-adjust timing under `[controls.market]` in `config.toml`.

## Buy `MAX`

`buy ... max` picks the matching entry from `[[controls.market.buy_hold_segments]]`, computes a hold from that segment's function and parameters, then clamps the result to `buy_max_hold_seconds`.

Relevant settings:

- `buy_max_hold_seconds`: hard cap for the final hold.
- `[[controls.market.buy_hold_segments]]`: ordered array of segment tables.
- `start`: inclusive cargo-ton threshold where that segment becomes active.
- `function`: `"flat"`, `"linear"`, or `"log"`.

Default example:

```toml
[controls.market]
buy_max_hold_seconds = 10.0

[[controls.market.buy_hold_segments]]
start = 0
function = "flat"
hold_seconds = 1.0

[[controls.market.buy_hold_segments]]
start = 100
function = "linear"
seconds_per_ton = 0.01

[[controls.market.buy_hold_segments]]
start = 301
function = "log"
base_seconds = -4.25
multiplier = 1.1829
```

The default shape is:

- `0-99t`: flat `1.0s`
- `100-300t`: linear at `0.01s/t`
- `301t+`: log taper

Segment selection is inclusive on `start`, using the last segment whose `start` is less than or equal to the cargo tons.

### Flat

Use this when a range should always hold for the same duration.

```toml
[[controls.market.buy_hold_segments]]
start = 0
function = "flat"
hold_seconds = 1.0
```

### Linear

Use this when a range should scale directly with cargo tons.

```toml
[[controls.market.buy_hold_segments]]
start = 100
function = "linear"
seconds_per_ton = 0.01
```

Formula:

```text
hold_seconds = tons * seconds_per_ton
```

With `120t` and `0.01s/t`, the hold is `1.2s`.

### Log

Use this when larger cargo amounts are overshooting and you want the curve to taper off.

```toml
[[controls.market.buy_hold_segments]]
start = 301
function = "log"
base_seconds = -4.25
multiplier = 1.1829
```

Formula:

```text
hold_seconds = base_seconds + log1p(tons) * multiplier
```

`log1p(tons)` means `ln(1 + tons)`, not `ln(tons)`.

Why that matters:

- `log(0)` is invalid, but `log1p(0)` is `0`
- it rises quickly at the low end, then tapers as cargo gets larger
- that taper makes it useful for large-capacity ships where linear timing overshoots

With the tuned default log parameters:

- `301t` is about `2.5s`
- `700t` is about `3.5s`

The log formula is clamped at `0` before the global max cap is applied, so a negative `base_seconds` is safe.

## Sell `MAX`

`sell ... max` restores quantity with rapid `UI_Right` taps instead of a long hold.

Relevant settings:

- `sell_quantity_restore_taps`: number of right taps used to restore the max quantity
- `sell_quantity_restore_tap_delay_seconds`: delay between those taps

Example:

```toml
[controls.market]
sell_quantity_restore_taps = 5
sell_quantity_restore_tap_delay_seconds = 0.05
```

If the sell dialog still undershoots on your setup, increase the tap count first, then add a little inter-tap delay if needed.
