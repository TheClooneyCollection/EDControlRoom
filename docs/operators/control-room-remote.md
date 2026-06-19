# Control Room Remote Observer Mode

This document covers the current `serve` / `connect` split for Control Room.

For normal embedded local use, start with [control-room.md](control-room.md).

## Purpose

Use remote observer mode when one machine should own the runtime and one or more other clients should watch or operate it over the LAN.

Current model:

- `serve` runs the authoritative Control Room runtime and journal watcher
- `connect` reuses the existing Textual Control Room UI as a remote client
- the first authenticated client becomes `active_operator` by default
- later authenticated clients join as read-only observers unless they claim operator
- one client can issue commands at a time; other clients only watch state, logs, and prompt progress
- TTS announcements are client-local only; the server streams announcement events but does not need to speak them
- server activity log lines are retained and also mirrored into server logs

## Commands

Start a server on the machine that owns the Elite runtime:

```sh
uv run python3 control_room.py serve --token 1001
uv run python3 control_room.py serve --host 0.0.0.0 --port 8765 --token 1001
```

Connect from a client:

```sh
uv run python3 control_room.py connect 192.168.1.50:8765 --token 1001
uv run python3 control_room.py connect 192.168.1.50:8765 --token 1001 --client-name bridge-ipad
uv run python3 control_room.py connect 192.168.1.50:8765 --token 1001 --claim-operator
```

## Operator Semantics

- command input is enabled only for the `active_operator`
- observers still receive snapshots, activity-log lines, announcements, prompt state, and replay state
- if the active operator disconnects, the next connected authenticated client is promoted automatically
- `Ctrl-C` on a connected client cancels the active remote routine or prompt flow instead of exiting immediately
- `Ctrl-D` starts a detach/exit confirmation flow; pressing it twice exits the client, and the default path is to leave the remote routine running

## Validation Runbook

Recommended LAN validation order:

1. On the server machine, start `serve` and confirm it prints no startup error about journals or config.
2. On client A, connect and verify the command bar is enabled immediately because the first client becomes active.
3. On client B, connect and verify the command bar is disabled and shows read-only observer state.
4. Run a safe command such as `market`, `commands`, or `replay` from client A and confirm both clients receive the same activity-log updates.
5. Trigger a TTS announcement path such as startup `Hello {title}` or a routine handoff and confirm only the clients speak it locally.
6. Start a prompt-heavy command such as `dest sol` or `haul`, then verify prompt transitions, default Enter submission, and `Ctrl-C` cancellation from the active client.
7. Disconnect client A and confirm client B is promoted automatically and can issue commands.
8. Reconnect a client and confirm it logs reconnect delay / restore messages and heals stale state from a fresh snapshot.

## Scratch Probe

For transport-only validation without launching the full Textual client, use:

```sh
uv run python3 tools/scratch/scratch_control_room_remote.py 192.168.1.50:8765 --token 1001
uv run python3 tools/scratch/scratch_control_room_remote.py 192.168.1.50:8765 --token 1001 --claim-operator --watch-seconds 10
```

The scratch probe fetches `health`, `capabilities`, and `snapshot`, then opens a websocket session and prints the message stream summary.

For a browser-native smoke check against the same LAN server, open:

```text
http://<server-host>:8765/browser-probe
```

The served page uses `fetch()` plus browser `WebSocket` directly against `GET /health`, `GET /capabilities`, `GET /snapshot`, `GET /schema/control_room_message.json`, and `WS /session`, and it can claim operator, submit command input, request snapshots, cancel active routines, and exercise replay-browser commands. It also mirrors the TUI client’s reconnect/backoff behavior so stale browser state heals from a fresh snapshot after transient disconnects, and it disables mutating controls while the browser session is only an observer.

If you want to open the same probe from disk instead of through the server, the source file still lives at:

```text
tools/scratch/control_room_remote_browser.html
```

## Current Caveats

- authentication is still a shared LAN token, not per-user auth
- the deepest remaining risk is live runtime behavior under real routine-heavy sessions, not protocol plumbing
- stale-market, wrong-station, and wrong-commodity recovery wording still needs more live validation
