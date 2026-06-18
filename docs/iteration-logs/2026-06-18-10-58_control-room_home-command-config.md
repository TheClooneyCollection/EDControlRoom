# Iteration Log

- Area: `control-room`
- Title: `home-command-config`
- Started: `2026-06-18 10:58`

## Summary

- Added a reusable `home` command that routes to `control_room.home_system`, plus `home set <system>` to persist that destination into config from Control Room itself.

## Changes

- Extended `ControlRoomConfig` with `home_system`, added config load coverage, and implemented a narrow TOML upsert helper that updates or creates a valid repo-root `config.toml` when the app was running from the default example-config fallback.
- Routed `home` through the existing `dest` flow so the normal galaxy-map settle prompt, history logging, and navigation behavior stay shared.
- Updated command help, placeholder text, `config.example.toml`, quickstart/operator docs, and README so the new route shortcut is discoverable.
- Added command/config tests for `home`, `home set`, existing-config updates, and fallback-config creation.
- Verified with `uv run python3 -m unittest discover -s tests` (`411` tests, `0.172s`).

## Follow-ups

- Live-check the new `home` shortcut and `home set` config write path against a real CrossOver-backed operator setup.
