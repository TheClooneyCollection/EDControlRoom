# Iteration Log

- Area: `control-room`
- Title: `hub-stop-waited-for-the-routine`
- Started: `2026-11-11 16:44`

## Summary

- Bug: Stop now on a hub page driving a peer took effect only after a long wait; on the peer's own page it was immediate.
- Cause: the peer answered each hub command, action and read with `asyncio.run(...)` on a relay thread. A routine start makes a Textual thread worker, whose task and `run_in_executor` live on that temporary loop, and `asyncio.run` waits for the default executor on close (up to 300 s, `THREAD_JOIN_TIMEOUT`). So the start's answer came only when the routine ended, and the channel's serial command runner (`PeerRelay._run_commands`) held the stop behind it. The hub page also got `node_unreachable` for the start after `command_timeout_s`.
- A local page is not affected: its handlers run on the server's long-lived loop, so `run_worker` returns at once.
- Not the cause: the per-channel serial queue itself (a local session also answers one message at a time), link heartbeat (frames are pushed, not polled), the hub page's `currentRoutine` (stale state would refuse, not delay).

## Changes

- `NodeLoop` in `edap/control_room/server/app.py`: one daemon event loop started on first use; `answer_node_command`, `answer_node_action` and `answer_node_read` run on it with `run_coroutine_threadsafe(...).result()`. Never called from the loop itself (the relay calls them on its own threads).
- `tests/test_hub_relay.py`: a hub page starts a routine on a real Textual thread worker of a never-run app (as the headless host does, `call_from_thread` called inline) and stops it; fails before the fix (start answered only after the routine's 2 s guard ran out), passes in about 10 ms after.
- The cut-off command test now runs peer commands on real threads, as live: with `run_now` the hub held its `HubRelay` RLock across the inline command, and the command's link drop needed that lock from the node loop thread.

## Follow-ups

- Not timed live with a hub and a peer (needs a game for a real routine); the unit test uses the same Textual worker path.
- Stop during a slow search or plot on the same page still waits for it, on a hub page and locally alike (both answer a page's messages in order). A fast lane for stop would need to decide what a stop means while `dispatch_route_all_in_one` is still plotting.
