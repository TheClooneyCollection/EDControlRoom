# Iteration Log

- Area: `ci-release`
- Title: `hub-branch-test-timing`
- Started: `2026-11-11 13:53`

## Summary

- The hub branch (plan 0015 steps 1-7) took the suite to 1135 tests at 0.66-0.72s, over the 0.0006s-per-test budget (0.681s). Per-file medians against `main`: `test_hub_relay` +39ms (new), `test_hub` +17ms, `test_control_room_server` +10ms. Nothing slept or polled; the cost was Starlette `TestClient` threads and Textual app construction.
- Now 0.595-0.606s over 5 runs (avg 0.599s, 0.00053s per test) with no test removed or merged.

## Changes

- `tests/test_control_room.py`: `_CachedThemeVariables` builds Textual's theme CSS variables once per theme instead of in every `App()` (about 40% of `_HarnessApp` construction); `_HarnessApp`, `_ProtocolHarnessApp` and the observer app in `test_control_room_client` use it. `_HarnessApp` also memoises `shutil.which` for the speech backend lookup. About -45ms.
- `tests/shared_loop.py`: a `TestClient` subclass that runs every app on one daemon event loop thread for the whole run instead of a new thread, loop and `to_thread` executor per `with TestClient(app)`. Lifespan still runs per client; WebSocket sessions use the same loop. The five server/hub/route test files import it in place of Starlette's. About -25ms.

## Follow-ups

- Measured and rejected: `gc.freeze()` or a higher GC threshold saved under 5ms here (Python 3.13 GC cost tracks allocations, not collection count); skipping `fsync` saved ~8ms but would need a production seam.
- A single gen2 GC pass (~10ms) lands on whichever test crosses the threshold, so one test can look 10ms slow in `report_test_timing.py` without being slow.
- Hub relay tests still cost ~2.5ms each (WebSocket sessions are ~0.6ms each through the TestClient thread hops); the next lever is fewer sessions per test, not cheaper ones.
