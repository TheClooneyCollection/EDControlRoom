# Scratch Tools

This directory groups exploratory probes and developer-only validation helpers that are intentionally not part of the main runtime surface.

Current scripts:

- `control_room_remote_browser.html`: browser-native HTTP/WebSocket probe for `serve`
- `scratch_cgevent.py`: early Quartz input probe
- `scratch_control_room_remote.py`: fetch remote observer HTTP surfaces and print websocket session events
- `scratch_inara_trade_routes.py`: headless-by-default Playwright probe for live Inara route rows
- `scratch_market.py`: `Market.json` inspector

Run them from the repo root with `uv run python3 tools/scratch/<script>.py ...`.
