# Iteration Log

- Area: `control-room`
- Title: `broker-serve-retained-snapshots`
- Started: `2026-06-19 12:27`

## Summary

- Moved `/snapshot`, websocket connection bootstrap, and `command.request_snapshot` onto the broker’s retained latest snapshot path so the session layer serves its current merged view instead of always asking the headless app for a fresh direct snapshot.

## Changes

- Added `InMemoryObserverSessionBroker.current_snapshot()` to return the retained merged snapshot when available and fall back to the runtime snapshot provider only when the broker has not seen state yet.
- Updated the observer HTTP and WebSocket server paths to prefer that retained broker snapshot for health/capabilities/snapshot responses, connection-ready bootstrap, and correlated snapshot requests.
- Added coverage proving `/snapshot` returns the broker-retained snapshot even when the provider would still report an older base view.
- Verified with `uv run python3 -m unittest tests/test_control_room_server.py` and `uv run python3 -m unittest discover -s tests`.

## Follow-ups

- Decide whether future web clients should read the retained broker snapshot directly through a thinner API layer instead of going back through the headless host at all.
- Keep moving prompt-flow and the remaining replay/session ownership off the app instance now that the broker has a clearer retained-snapshot seam.
