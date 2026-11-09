# Iteration Log

- Area: `control-room`
- Title: `reload-config-command`
- Started: `2026-11-09 12:07`

## Summary

- New `reload_config` command so a Deck config tweak (here `controls.market.nav_delay_seconds = 0.2` against dropped list presses) no longer needs a server restart that kills the running haul.

## Changes

- `ControlRoomApp._cmd_reload_config` loads `_config_path`, swaps `_config` and `_ctx.config`, rebuilds controls (hold settings) and calls `TTSAnnouncer.apply_wording` (title, phrases, disabled messages; the speech backend and on/off stay as built).
- Routines read `app._config` when they start, so market, haul and timing settings take effect from the next routine. Anything built once at startup (paths, input controller, timing sampler, Piper voice, server host/port/state files) still needs a restart; the command says so.
- Refused while a routine runs, like `reload_keymap`; a parse or validation error keeps the running config.

## Follow-ups

- Not yet exercised live on the Deck.
