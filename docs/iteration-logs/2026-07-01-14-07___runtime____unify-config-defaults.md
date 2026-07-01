# Iteration Log

- Area: `runtime`
- Title: `unify-config-defaults`
- Started: `2026-07-01 14:07`

## Summary

- Unified shipped app defaults under `defaults/*.toml` and kept ignored local TOML files as override layers.
- Stopped tracking repo-root `haul.toml` while preserving `haul load` as the local profile workflow.

## Changes

- Added default category files for paths, runtime, controls, screen, haul, and haul search; expanded `defaults/control_room.toml` to carry the full Control Room defaults.
- Changed `edap.config.load_config()` to merge local config over shipped category defaults before validation, so minimal `config.toml` files only need explicit overrides.
- Converted `config.example.toml` into an override skeleton, moved Inara search defaults to `defaults/haul_search.toml`, and raised the default haul docking timeout to `1200s`.

## Follow-ups

- Live-validate the `1200s` haul docking timeout against slower carrier/station approaches and keep local `haul.toml` guidance aligned with operator feedback.
