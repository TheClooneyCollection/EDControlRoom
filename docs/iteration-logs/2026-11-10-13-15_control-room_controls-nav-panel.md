# Iteration Log

- Area: `control-room`
- Title: `controls-nav-panel`
- Started: `2026-11-10 13:15`

## Summary

- `/controls` lacked the TUI navigation commands (`dest`, `travel`, `home`). Added a Nav panel; `set_input` and `verbose` were deliberately left out at the user's request.

## Changes

- `web/controls.html` / `web/controls.js`: Nav panel with System, Station and a Surface port checkbox, plus Plot route (`command.dispatch_destination` with the configured galaxy-map settle), Travel (`command.dispatch_travel`, `on_land` only with a station), Plot home and Set home (`home set`, current system when the field is empty). All need an idle routine.
- `edap/control_room/dependencies.py`: web form defaults include `homeSystem`, so Plot home dispatches by name instead of going through the TUI `home` prompt flow; the page refreshes it from each hydrate.
- Rendered headless at desktop and 390 px widths against the LAN page with no JS errors.

## Follow-ups

- Full suite runs about 0.61-0.63 s for 990 tests on a busy machine, above the 0.594 s budget even without this change; recheck on an idle machine.
