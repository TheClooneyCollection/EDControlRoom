# Iteration Log

- Area: `control-room`
- Title: `validate-remote-capabilities-handshake`
- Started: `2026-06-19 18:17`

## Summary

- Hardened the remote client handshake so `connect` fails clearly against incomplete or incompatible capability surfaces instead of discovering protocol mismatches only after the websocket session starts.

## Changes

- Added client-side validation of `supported_message_types`, `supported_client_roles`, and `minimum_client_version` during the authenticated `/capabilities` fetch.
- Added focused client tests covering the accepted current server surface, missing required message types, and unsupported minimum client versions.
- Updated the remote operator docs and current control-room status handoff to note that incompatible servers are now rejected during the capability probe.

## Follow-ups

- If the remote protocol adds or removes required message types later, keep the client-side compatibility gate and the server-side advertised capability set updated in the same change.
