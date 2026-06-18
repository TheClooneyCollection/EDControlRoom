# Market Timing

EDControlRoom exposes a small set of market quantity-adjust timing controls under `[controls.market]` in `config.toml`.

## Buy `MAX`

`buy ... max` computes a hold duration from the effective cargo tons to buy, then clamps it to `buy_max_hold_seconds`.

Relevant settings:

- `buy_max_hold_seconds`: hard cap for the buy hold.
- `buy_hold_timing_function`: `"linear"` or `"log"`.
- `buy_hold_seconds_per_ton`: linear-mode multiplier.
- `buy_hold_log_base_seconds`: fixed base added in log mode.
- `buy_hold_log_multiplier`: log-mode multiplier.

Linear mode:

```toml
[controls.market]
buy_max_hold_seconds = 10.0
buy_hold_timing_function = "linear"
buy_hold_seconds_per_ton = 0.01
```

Formula:

```text
hold_seconds = min(buy_max_hold_seconds, tons * buy_hold_seconds_per_ton)
```

With `300t` and `0.01s/t`, the hold is `3.0s`.

Log mode:

```toml
[controls.market]
buy_max_hold_seconds = 10.0
buy_hold_timing_function = "log"
buy_hold_log_base_seconds = 0.0
buy_hold_log_multiplier = 0.35
```

Formula:

```text
hold_seconds = min(buy_max_hold_seconds, buy_hold_log_base_seconds + log1p(tons) * buy_hold_log_multiplier)
```

With `300t`, `base = 0.0`, and `multiplier = 0.35`, the hold is about `2.0s`.

Use `linear` when you already trust a direct seconds-per-ton ratio. Use `log` when larger cargo amounts are overshooting and you want the curve to taper off.

## Sell `MAX`

`sell ... max` now restores quantity with rapid `UI_Right` taps instead of a long hold.

Relevant settings:

- `sell_quantity_restore_taps`: number of right taps used to restore the max quantity.
- `sell_quantity_restore_tap_delay_seconds`: delay between those taps.

Example:

```toml
[controls.market]
sell_quantity_restore_taps = 5
sell_quantity_restore_tap_delay_seconds = 0.05
```

If the sell dialog still undershoots on your setup, increase the tap count first, then add a little inter-tap delay if needed.
