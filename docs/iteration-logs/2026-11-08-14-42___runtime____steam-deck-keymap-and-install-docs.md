# Iteration Log

- Area: `runtime`
- Title: `steam-deck-keymap-and-install-docs`
- Started: `2026-11-08 14:42`

## Summary

- New Steam Deck users needed the keyboard keys routines press added to their controller preset by hand. `tools/deck_keymap.py` now does it in one step, and the install docs describe the real Deck install (uv in `~/.local/bin`, clone, `uv sync`, uinput, no `config.toml`) instead of the old untested xdotool notes.

## Changes

- `edap/deck_keymap.py`: `DECK_KEYMAP` (Elite KeyboardMouseOnly defaults where they exist; arrows for menu directions; roll `,` `.`, pitch `I` `K`, `SetSpeed100` F5, `HeadLookReset` F6, `GalaxyMapOpen` F7 for actions with no keyboard default) and `plan_deck_keymap`, which fills empty slots Secondary first, keeps any user keyboard key, replaces only bare WASD on `UI_*`, and never touches controller bindings.
- `tools/deck_keymap.py`: prints the plan; `--write` applies it after a backup that never overwrites an older `.bak`.
- Checked against Elite's shipped `ConsoleX360.binds` (the Deck preset's base): 13 changes, then every keymap action resolves and no galaxy-map warning. On the user's current Deck file it changes nothing.
- README gains a Steam Deck section; `docs/user/install.md` replaces "Linux (untested)" with a Steam Deck / Linux section.

## Follow-ups

- Semicolon was avoided: Elite's token spelling for it is unverified and the lookup only knows `Key_Semicolon`.
