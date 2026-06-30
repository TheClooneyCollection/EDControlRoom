# Iteration Log

- Area: `control-room`
- Title: `add-dest-remote-debug-logging`
- Started: `2026-06-30 14:13`

## Summary

- Added targeted debug logging around the remote `dest` flow so the next manual `serve` + `connect` reproduction will show exactly where a post-prompt failure occurs.

## Changes

- Logged observer-side destination prompt resolution before `command.dispatch_destination` is sent.
- Logged headless server receipt of destination dispatch payloads and routine-launch inputs for remote `dest` runs.
- Logged full routine exception metadata and traceback into `artifacts/control-room-debug.log` when a background routine crashes.

## Follow-ups

- Reproduce the failing `dest sol` settle-seconds submission in a real interactive connect session, then inspect `artifacts/control-room-debug.log` for the new `observer_dest_prompt_dispatch_resolved`, `server_dispatch_destination_received`, and `routine_thread_exception` events.
