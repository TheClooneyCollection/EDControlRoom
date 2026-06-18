# Iteration Log

- Area: `runtime`
- Title: `status-file-autodock-flags-note`
- Started: `2026-06-18 23:25`

## Summary

- Checked the Elite Journal `Status File` reference against the current `edap/status.py` parser to answer whether `Status.json` can reveal auto-docking or auto-launch state.

## Changes

- Confirmed the repo already matches the documented `Flags` table used by `Status.json`.
- Confirmed the documented `Flags2` table adds on-foot, glide, FSD-hyperdrive, SCO, and supercruise-assist state, but no auto-docking or auto-launch bits.
- Updated `docs/status/runtime.md` so the runtime handoff explicitly states that docking-computer state still comes from journal/music cues rather than `Status.json`.

## Follow-ups

- If operator UX needs more status-file visibility later, add `Flags2` parsing for documented fields such as `Supercruise Assist Active`, but do not expect it to answer autodock/autolaunch.
