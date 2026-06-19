# Iteration Log

- Area: `control-room`
- Title: `remote-prompt-interrupt`
- Started: `2026-06-19 14:10`

## Summary

- Fixed the remote `Ctrl-C` gap where active-operator clients could cancel routines but could not back out of prompt flows like haul setup, haul confirm, or destination settle.

## Changes

- Added a shared prompt-cancellation helper in `edap/control_room/prompts.py` that clears prompt state, restores the command placeholder, and logs the cancelled flow.
- Routed both local backend interrupts and headless server-host remote interrupts through the same app-level `_handle_interrupt()` path so prompt cancellation runs before routine cancellation.
- Added regressions covering local prompt `Ctrl-C`, remote-client prompt `Ctrl-C` forwarding, and remote host prompt-state clearing plus snapshot publication.

## Follow-ups

- Live-validate remote active-operator prompt cancellation against real haul and destination flows under `serve` / `connect`.
