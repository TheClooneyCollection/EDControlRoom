# Input Timing

EDControlRoom exposes human-style timing variation under `[timing]` in `config.toml`.

This affects only human-facing input timing:

- command launch delays
- routine sleep delays
- gaps between repeated button presses
- held-key dwell time
- typing cadence

It does not affect background housekeeping like journal polling or status refresh cadence.

## What The Default Behavior Does

The default timing model adds small variation around your configured delay instead of using the exact same number every time.

In plain language:

- most actions stay close to the configured value
- some actions are a bit faster
- some actions are a bit slower
- very extreme values are clipped so timing stays within a safe band

That gives you timing that feels less mechanical without turning into chaos.

## Config Shape

```toml
[timing]
enabled = true
distribution = "log_normal"

[timing.delay]
sigma = 0.18
min_factor = 0.85
max_factor = 1.35
min_seconds = 0.0

[timing.hold]
sigma = 0.12
min_factor = 0.9
max_factor = 1.2
min_seconds = 0.02

[timing.typing]
sigma = 0.28
min_factor = 0.65
max_factor = 1.75
min_seconds = 0.02
```

## Top-Level Settings

- `enabled`: turns timing variation on or off.
- `distribution`: the sampling shape. Right now only `"log_normal"` is supported.

If `enabled = false`, EDControlRoom uses the exact configured delay values with no randomization.

## The Three Timing Channels

### `timing.delay`

Used for waits between actions:

- Control Room command delay
- routine pauses
- gaps between repeated taps

### `timing.hold`

Used when a key is intentionally held down for a short time before release.

Examples:

- a tap with `hold_s`
- a button press that needs a little dwell to register reliably

### `timing.typing`

Used for time between typed characters.

This usually wants the widest variation so typed text does not look metronomic.

## What Each Field Means

### `sigma`

Think of `sigma` as “how much wobble to allow.”

- lower `sigma`: timings stay closer to the base value
- higher `sigma`: timings spread out more

Good rule of thumb:

- `0.0`: no variation
- `0.1 - 0.2`: subtle variation
- `0.25 - 0.35`: noticeable variation
- higher than that: likely too loose for menu-driven routines

### `min_factor`

The fastest allowed result, as a fraction of the base value.

Examples:

- `0.85` means “never go below 85% of the configured delay”
- `1.0` means “never go faster than the configured delay”

If your configured delay is `1.0s` and `min_factor = 0.85`, the randomized result will never be less than `0.85s`.

### `max_factor`

The slowest allowed result, as a multiple of the base value.

Examples:

- `1.35` means “never go above 135% of the configured delay”
- `1.0` means “never go slower than the configured delay”

If your configured delay is `1.0s` and `max_factor = 1.35`, the randomized result will never exceed `1.35s`.

### `min_seconds`

A hard floor in seconds.

This is most useful for very short timings that still need a minimum practical dwell.

Example:

- base hold is `0.01s`
- sampled value tries to go even lower
- `min_seconds = 0.02`
- final result becomes `0.02s`

## Easy Tuning Advice

If you want timing to be:

- more consistent: lower `sigma`, tighten `min_factor`/`max_factor` toward `1.0`
- more varied: raise `sigma`, widen the factor range a little
- never too short: raise `min_factor` or `min_seconds`
- never too slow: lower `max_factor`

## Safe Starting Presets

### No Randomization

```toml
[timing]
enabled = false
distribution = "log_normal"
```

### Very Conservative Variation

```toml
[timing]
enabled = true
distribution = "log_normal"

[timing.delay]
sigma = 0.1
min_factor = 0.95
max_factor = 1.1
min_seconds = 0.0

[timing.hold]
sigma = 0.08
min_factor = 0.95
max_factor = 1.1
min_seconds = 0.02

[timing.typing]
sigma = 0.15
min_factor = 0.85
max_factor = 1.25
min_seconds = 0.02
```

### More Human-Looking Typing, Stable Menu Timing

```toml
[timing]
enabled = true
distribution = "log_normal"

[timing.delay]
sigma = 0.15
min_factor = 0.9
max_factor = 1.2
min_seconds = 0.0

[timing.hold]
sigma = 0.1
min_factor = 0.95
max_factor = 1.15
min_seconds = 0.02

[timing.typing]
sigma = 0.3
min_factor = 0.6
max_factor = 1.8
min_seconds = 0.02
```

## Practical Recommendation

If a routine becomes flaky after enabling timing variation:

1. tighten `timing.delay` first
2. then tighten `timing.hold`
3. leave `timing.typing` looser unless text entry itself is the problem

For most operators, the default values should be the right starting point.
