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

- the local server process remains the initial `active_operator`
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

The first implementation should require a shared access token for `GET /snapshot`, `GET /capabilities`, and `WS /session`.

- accept `Authorization: Bearer <token>` on HTTP requests
- accept `access_token=<token>` on the WebSocket query string so browser clients remain viable
- `GET /health` may stay unauthenticated for simple liveness checks

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
- `event.announcement_emitted`
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

### `response.capabilities`

Payload:

- `capability_names`
- `supported_client_roles`
- `supported_message_types`
- `minimum_client_version`
- `server_version`
- `authentication_required`
- `authentication_scheme`
- `authentication_supported_transports`
- `authentication_query_parameter_name`

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
- `ship`
- `market`
- `haul_session`
- `ui_state`
- `command_history`
- `prompt_state`
- `replay_browser`
- `activity_log`
- `server_status`

The first concrete snapshot shape should mirror the current `ControlRoomApp` state model rather than inventing a second parallel model.

#### `session`

- `session_id`
- `client_role`

#### `ship`

Derived from `ShipState` and the status bootstrap path.

- `commander_name`
- `ship_type`
- `system_name`
- `station_name`
- `status`
- `fuel_level`
- `fuel_capacity`
- `credits`
- `cargo_count`
- `cargo_capacity`
- `cargo_inventory`
- `target_name`
- `destination_system`
- `destination_body`
- `destination_name`

#### `market`

Derived from `MarketData` plus the active filter text.

- `station_name`
- `system_name`
- `market_timestamp`
- `market_filter_text`
- `locked`
- `items`

#### `haul_session`

Derived from `HaulStats`.

- `station_1_buying`
- `station_2_buying`
- `station_1`
- `station_2`
- `active`
- `clean_run_active`
- `waiting_for_station_1_departure`
- `resumed_mid_run`
- `docked_back_at_station_1`
- `current_run_started_at`
- `current_run_elapsed_seconds`
- `current_run_profit`
- `completed_runs`
- `accumulated_profit`
- `last_run_profit`
- `last_run_elapsed_seconds`
- `total_run_elapsed_seconds`

#### `ui_state`

Derived from `RuntimeUIState` plus visible UI mode flags the app already owns.

- `routine_active`
- `active_routine_name`
- `haul_stop_requested`
- `verbose_controls`
- `instant_mode`
- `activity_auto_follow_paused`
- `replay_browser_open`
- `shutdown_requested`
- `shutdown_finalized`

#### `command_history`

Derived from `ControlRoomState`, `HistoryState`, and config.

- `default_haul`
- `history_entries`
- `history_limit`
- `draft_command`
- `replay_filter_text`

Each `history_entries` item should carry:

- `raw_command`
- `command_name`
- `arguments`
- `timestamp`

#### `prompt_state`

Derived from `PromptState`.

- `haul_parameters`
- `haul_prompt_defaults`
- `haul_prompt_step`
- `haul_confirm_buy_station`
- `haul_prompt_raw_command`
- `haul_prompt_skip_delay`
- `destination_prompt_destination`
- `destination_prompt_settle_default`
- `destination_prompt_raw_command`
- `destination_prompt_skip_delay`

#### `replay_browser`

Derived from `ReplayBrowserState` and the already-built replay entry list.

- `open`
- `filter_text`
- `visible_entries`
- `selected_history_entry`

Each `visible_entries` item should carry:

- `label`
- `detail`
- `history_entry`

#### `activity_log`

This remains a normalized protocol view rather than a raw serialization of Textual widget internals.

- each entry should carry at least `timestamp`, `message_text`, and `severity`
- the server may synthesize stable `entry_id` values when it emits or snapshots log entries
- live additions should be streamed with `event.activity_log_appended`

#### announcement streaming

Announcements should be streamed separately from the durable activity log.

- use `event.announcement_emitted` for TTS-style notification intent that clients may announce locally
- use `event.activity_log_appended` for durable operator timeline entries
- when a server-side action should be both durable and announceable, emit both events

This keeps browser and remote-native clients free to make separate decisions about:

- speaking audio
- recording a durable timeline item

#### `server_status`

This should be derived from the runtime context rather than from UI widgets.

- `server_name`
- `server_version`
- `runtime_platform`
- `journal_source_status`
- `bindings_source_status`
- `bindings_loaded`
- `capability_names`
- `operator_mode`

`alerts` should not be part of the required first snapshot because the current app does not maintain a separate alert store yet.

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

### `event.announcement_emitted`

Payload:

- `announcement_id`
- `message_text`
- `message_values`

The event represents announcement intent only. Clients may perform local TTS if configured to do so. The protocol does not report whether the server itself spoke the message.

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
- Start `control_room connect` as an observer-only client path that fetches a snapshot, subscribes to the event stream, and performs local TTS from streamed announcement identifiers using the client machine's own config.
- Keep the server authoritative. Clients request work; the server decides and reports state.
- Enforce command authority on the server. Observer clients must receive a clear `response.error` if they attempt an operator-only command.
- Use `state.snapshot` plus event streaming instead of mirroring internal method calls over the wire.
- Include `version` in every message so incompatible changes fail explicitly.
- Use `correlation_message_id` for responses and any asynchronous follow-up event that should be tied to a specific client command.
- Treat operator-facing messages as protocol data, not client-side string reconstruction.

## Security and Exposure

- bind to `127.0.0.1` by default
- require an explicit listen host such as `0.0.0.0` to expose on LAN
- require shared-token authentication from the first implementation, even on localhost/LAN observer mode
- start with a shared token or pairing code, not anonymous LAN control

## Web Client Readiness

This design is intentionally browser-friendly.

- HTTP plus WebSocket works directly in browsers
- JSON payloads are easy to inspect in browser tooling
- snapshot-plus-events maps cleanly to a future web UI state store

If payload size becomes a real constraint later, the same envelope can carry MessagePack or a schema-backed binary form in a future protocol version without redesigning the control model first.
