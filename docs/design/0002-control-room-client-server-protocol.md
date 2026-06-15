# 0002: Control Room Client/Server Protocol

## Status

Draft

## Purpose

Define the first network shape for splitting Control Room into a server that owns the Elite runtime and one or more clients that render operator surfaces and send commands.

The immediate target is local-LAN control between one Control Room client and another Control Room server. The protocol must also leave a clean path for future web clients.

## Transport Choice

Use HTTP plus WebSocket.

- HTTP handles health checks, server discovery helpers, and one-shot snapshot fetches.
- WebSocket handles the long-lived bidirectional control session.
- JSON is the first payload format because it is simple to inspect, simple to debug, and browser-native.

Do not start with raw TCP, gRPC, or WebRTC.

- raw TCP adds custom framing and browser incompatibility with no clear upside for the current scope
- gRPC adds browser gateway complexity too early
- WebRTC solves a different class of problems than this control plane needs

## Topology

- the server runs on the machine that has Elite Dangerous runtime access
- the server is authoritative for routines, bindings lookup, journal state, activity log, and operator-visible runtime state
- the client renders a local or remote Control Room surface and sends protocol commands
- exactly one connected client may hold the active operator role at a time
- additional connected clients may attach as observer clients that receive snapshots and live events but cannot issue runtime-changing commands

## Client Roles

The first implementation should support two roles:

- `active_operator`: may issue routine and UI-mutating commands
- `observer`: read-only session that may request snapshots but may not issue runtime-changing commands

The server should assign these roles, not trust the client to self-assert them.

Recommended first policy:

- the first authenticated interactive client becomes `active_operator`
- later clients default to `observer`
- a localhost client may optionally preempt the active operator later, but that is a follow-up policy decision, not a day-one requirement

## CLI Direction

- `control_room serve` starts the server
- `control_room connect <host>:<port>` starts a remote client session
- plain `control_room` may remain as an embedded local mode during the transition

## HTTP Surface

Minimum first endpoints:

- `GET /health` for liveness and basic version information
- `GET /snapshot` for a current state snapshot that matches the WebSocket `state.snapshot` payload family
- `GET /capabilities` for server feature discovery if an HTTP probe is needed before opening a session

## WebSocket Session

The session should use one versioned JSON envelope for every command, event, state push, and response.

Required envelope fields:

- `schema`
- `version`
- `message_type`
- `message_id`
- `timestamp`
- `payload`

Optional envelope fields:

- `correlation_message_id` for replies or follow-up events tied to a prior command

Recommended envelope example:

```json
{
  "schema": "edcontrolroom.control_room_message",
  "version": 1,
  "message_type": "command.run_routine",
  "message_id": "message-000123",
  "timestamp": "2026-06-15T14:45:00Z",
  "payload": {
    "routine_name": "market_sell",
    "arguments": {
      "commodity_name": "silver"
    }
  }
}
```

## Vocabulary

### Session and capability

- `command.authenticate`
- `response.authentication_result`
- `response.capabilities`
- `event.active_operator_changed`

### Client commands

- `command.request_snapshot`
- `command.run_routine`
- `command.cancel_routine`
- `command.set_market_filter`
- `command.clear_market_filter`
- `command.dismiss_alert`

### Server state pushes

- `state.snapshot`

### Server events

- `event.connection_ready`
- `event.operator_message`
- `event.activity_log_appended`
- `event.routine_started`
- `event.routine_progress`
- `event.routine_failed`
- `event.routine_completed`
- `event.routine_cancelled`
- `event.server_warning`

### Command responses

- `response.success`
- `response.error`

## Payload Contracts

### `command.authenticate`

Sent immediately after connection if the server requires a shared token or pairing secret.

Payload:

- `authentication_token`
- `client_name`
- `client_version`

### `response.authentication_result`

Payload:

- `authenticated`
- `server_name`
- `server_version`
- `session_id`
- `client_role`
- `capability_names`
- `operator_mode`

### `response.capabilities`

Payload:

- `capability_names`
- `supported_client_roles`
- `supported_message_types`
- `minimum_client_version`
- `server_version`

### `command.request_snapshot`

Payload:

- `include_activity_log`
- `include_market_state`

### `state.snapshot`

Payload should be a complete renderable view for a newly connected client.

Payload:

- `session`
- `connected_clients`
- `active_operator`
- `commander`
- `location`
- `ship`
- `cargo`
- `market`
- `current_routine`
- `activity_log`
- `alerts`
- `server_status`

### `command.run_routine`

Payload:

- `routine_name`
- `arguments`

The server should treat `arguments` as a routine-specific object and validate it per routine before execution.

### `command.cancel_routine`

Payload:

- `routine_id`
- `reason`

### `command.set_market_filter`

Payload:

- `filter_text`

### `command.clear_market_filter`

Payload:

- empty object

### `command.dismiss_alert`

Payload:

- `alert_id`

### `event.connection_ready`

Payload:

- `session_id`
- `server_name`
- `server_version`
- `client_role`
- `capability_names`

### `event.active_operator_changed`

Payload:

- `active_operator_session_id`
- `active_operator_client_name`
- `reason`

### `event.operator_message`

Payload:

- `severity`
- `message_text`
- `recommended_action`

### `event.activity_log_appended`

Payload:

- `entry`

### `event.routine_started`

Payload:

- `routine_id`
- `routine_name`
- `arguments`

### `event.routine_progress`

Payload:

- `routine_id`
- `progress_message`
- `progress_detail`

### `event.routine_failed`

Payload:

- `routine_id`
- `failure_code`
- `failure_message`
- `recommended_action`

### `event.routine_completed`

Payload:

- `routine_id`
- `completion_message`
- `result`

### `event.routine_cancelled`

Payload:

- `routine_id`
- `cancellation_reason`

### `event.server_warning`

Payload:

- `warning_code`
- `warning_message`
- `recommended_action`

### `response.success`

Payload:

- `accepted`
- `message_text`
- `result`

### `response.error`

Payload:

- `error_code`
- `error_message`
- `recommended_action`
- `retryable`

## Design Rules

- Use full property names throughout the protocol. No abbreviated wire fields.
- Keep the server authoritative. Clients request work; the server decides and reports state.
- Enforce command authority on the server. Observer clients must receive a clear `response.error` if they attempt an operator-only command.
- Use `state.snapshot` plus event streaming instead of mirroring internal method calls over the wire.
- Include `version` in every message so incompatible changes fail explicitly.
- Use `correlation_message_id` for responses and any asynchronous follow-up event that should be tied to a specific client command.
- Treat operator-facing messages as protocol data, not client-side string reconstruction.

## Security and Exposure

- bind to `127.0.0.1` by default
- require an explicit listen host such as `0.0.0.0` to expose on LAN
- require authentication for non-localhost sessions from the first implementation
- start with a shared token or pairing code, not anonymous LAN control

## Web Client Readiness

This design is intentionally browser-friendly.

- HTTP plus WebSocket works directly in browsers
- JSON payloads are easy to inspect in browser tooling
- snapshot-plus-events maps cleanly to a future web UI state store

If payload size becomes a real constraint later, the same envelope can carry MessagePack or a schema-backed binary form in a future protocol version without redesigning the control model first.
