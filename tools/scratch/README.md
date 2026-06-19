# Scratch Tools

This directory groups exploratory probes and developer-only validation helpers that are intentionally not part of the main runtime surface.

Current scripts:

- `scratch_cgevent.py`: early Quartz input probe
- `scratch_control_room_remote.py`: fetch remote observer HTTP surfaces and print websocket session events
- `scratch_cv.py`: one-shot CV template matcher
- `scratch_market.py`: `Market.json` inspector
- `scratch_rebake.py`: template rebake helper

Run them from the repo root with `uv run python3 tools/scratch/<script>.py ...`.
