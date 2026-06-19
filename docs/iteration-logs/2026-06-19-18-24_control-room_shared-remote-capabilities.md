# Iteration Log

- Area: `control-room`
- Title: `shared-remote-capabilities`
- Started: `2026-06-19 18:24`

## Summary

- Collapsed the remote observer capability surface into one shared protocol module so server discovery, client validation, and capability-focused tests stop drifting independently.

## Changes

- Added `edap/control_room/protocol/capabilities.py` with shared message-role/auth constants plus helpers to build and validate the observer capability payload.
- Rewired the observer server capability endpoint and shared-token auth description to use the shared capability constants instead of local duplicated literals.
- Rewired the remote client capability validation and tests to use the shared builder/validator rather than repeated hand-written capability dictionaries, and tightened validation so the advertised command/event/response breakdown lists must stay aligned with the aggregate message list.
- Updated the hosted browser probe to consume the advertised websocket auth query-parameter metadata from `GET /capabilities` instead of hardcoding `access_token`, so the browser path now behaves like a discovery-driven future web client.
- Updated the CLI scratch probe to validate the advertised capability surface, build its websocket URL from the same auth metadata, and log the correct active-operator change field so the non-TUI validation helpers no longer drift from the real remote contract.
- Updated the native Textual client and CLI scratch probe to prefer websocket bearer-header auth and reserve the query-parameter path for browser-constrained clients, keeping the shared capability contract but avoiding URL token transport where the runtime does not need it.
- Kept schema validation anchored to the shared protocol message-type list and verified the full suite stayed green.

## Follow-ups

- Run the live remote validation playbook so the next server/client slices focus on runtime behavior rather than protocol-contract drift.
