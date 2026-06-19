# Iteration Log

- Area: `control-room`
- Title: `validate-remote-auth-and-discovery-handshake`
- Started: `2026-06-19 18:19`

## Summary

- Extended the remote client compatibility gate so `connect` now rejects capability surfaces that are message-compatible but still missing the auth transports or discovery fields the current remote clients actually depend on.

## Changes

- Added client-side validation for `authentication_required`, `authentication_scheme`, `authentication_supported_transports`, `authentication_query_parameter_name`, `message_schema_url`, and `browser_probe_url` during the authenticated capability probe.
- Added focused client tests covering missing auth transports and missing discovery URLs in addition to the existing message/version checks.
- Updated the remote operator docs and current control-room status handoff to note that incompatible auth/discovery capability surfaces now fail before websocket startup.

## Follow-ups

- If the remote transport contract changes again, keep the client handshake validator focused on the fields that real clients actually consume instead of treating `/capabilities` as a passive info blob.
