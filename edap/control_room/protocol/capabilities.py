from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import quote


ACCESS_TOKEN_QUERY_PARAMETER = "access_token"
AUTHENTICATION_SCHEME_BEARER_TOKEN = "bearer_token"
MINIMUM_CLIENT_VERSION = "1"
SUPPORTED_CLIENT_ROLES = ["active_operator", "observer"]
SUPPORTED_COMMAND_MESSAGE_TYPES = [
    "command.request_active_operator",
    "command.submit_input",
    "command.dispatch_destination",
    "command.dispatch_haul_loop",
    "command.search_haul_routes",
    "command.select_trade_route",
    "command.cancel_active_routine",
]
SUPPORTED_EVENT_MESSAGE_TYPES = [
    "event.connection_ready",
    "event.active_operator_changed",
    "event.activity_log_appended",
    "event.announcement_emitted",
]
SUPPORTED_RESPONSE_MESSAGE_TYPES = [
    "response.success",
    "response.error",
]
SUPPORTED_MESSAGE_TYPES = [
    *SUPPORTED_EVENT_MESSAGE_TYPES,
    *SUPPORTED_COMMAND_MESSAGE_TYPES,
    *SUPPORTED_RESPONSE_MESSAGE_TYPES,
]
REQUIRED_AUTHENTICATION_TRANSPORTS = [
    "authorization_header",
    "query_parameter",
]


@dataclass(frozen=True)
class RemoteObserverWebSocketConnectInfo:
    session_url: str
    additional_headers: tuple[tuple[str, str], ...] = ()


def build_remote_observer_capabilities_payload(
    *,
    capability_names: Sequence[str],
    server_version: str,
    authentication_required: bool,
    authentication_scheme: str,
    authentication_supported_transports: Sequence[str],
    authentication_query_parameter_name: str | None,
    message_schema_url: str,
    browser_probe_url: str,
) -> dict[str, object]:
    return {
        "capability_names": list(capability_names),
        "supported_client_roles": list(SUPPORTED_CLIENT_ROLES),
        "supported_message_types": list(SUPPORTED_MESSAGE_TYPES),
        "supported_command_message_types": list(SUPPORTED_COMMAND_MESSAGE_TYPES),
        "supported_event_message_types": list(SUPPORTED_EVENT_MESSAGE_TYPES),
        "supported_response_message_types": list(SUPPORTED_RESPONSE_MESSAGE_TYPES),
        "minimum_client_version": MINIMUM_CLIENT_VERSION,
        "server_version": server_version,
        "message_schema_url": message_schema_url,
        "browser_probe_url": browser_probe_url,
        "authentication_required": authentication_required,
        "authentication_scheme": authentication_scheme,
        "authentication_supported_transports": list(authentication_supported_transports),
        "authentication_query_parameter_name": authentication_query_parameter_name,
    }


def validate_remote_observer_capabilities_payload(
    capabilities: Mapping[str, Any],
) -> str | None:
    supported_command_message_types = capabilities.get("supported_command_message_types")
    if not _is_string_list(supported_command_message_types):
        return "supported_command_message_types must be a string list."
    missing_command_message_types = sorted(
        set(SUPPORTED_COMMAND_MESSAGE_TYPES).difference(supported_command_message_types)
    )
    if missing_command_message_types:
        return (
            "does not support required command message types: "
            f"{', '.join(missing_command_message_types)}"
        )

    supported_event_message_types = capabilities.get("supported_event_message_types")
    if not _is_string_list(supported_event_message_types):
        return "supported_event_message_types must be a string list."
    missing_event_message_types = sorted(
        set(SUPPORTED_EVENT_MESSAGE_TYPES).difference(supported_event_message_types)
    )
    if missing_event_message_types:
        return (
            "does not support required event message types: "
            f"{', '.join(missing_event_message_types)}"
        )

    supported_response_message_types = capabilities.get("supported_response_message_types")
    if not _is_string_list(supported_response_message_types):
        return "supported_response_message_types must be a string list."
    missing_response_message_types = sorted(
        set(SUPPORTED_RESPONSE_MESSAGE_TYPES).difference(supported_response_message_types)
    )
    if missing_response_message_types:
        return (
            "does not support required response message types: "
            f"{', '.join(missing_response_message_types)}"
        )

    supported_message_types = capabilities.get("supported_message_types")
    if not _is_string_list(supported_message_types):
        return "supported_message_types must be a string list."
    missing_message_types = sorted(set(SUPPORTED_MESSAGE_TYPES).difference(supported_message_types))
    if missing_message_types:
        return f"does not support required message types: {', '.join(missing_message_types)}"
    expected_message_types = [
        *supported_event_message_types,
        *supported_command_message_types,
        *supported_response_message_types,
    ]
    if set(supported_message_types) != set(expected_message_types):
        return (
            "supported_message_types must match the union of the advertised command, event, "
            "and response message types."
        )

    supported_client_roles = capabilities.get("supported_client_roles")
    if not _is_string_list(supported_client_roles):
        return "supported_client_roles must be a string list."
    if any(role not in supported_client_roles for role in SUPPORTED_CLIENT_ROLES):
        return "does not advertise both active_operator and observer roles."

    minimum_client_version = capabilities.get("minimum_client_version")
    if minimum_client_version != MINIMUM_CLIENT_VERSION:
        return f"requires unsupported client version {minimum_client_version!r}."

    authentication_required = capabilities.get("authentication_required")
    if authentication_required is not True:
        return "must require authentication for observer mode."

    authentication_scheme = capabilities.get("authentication_scheme")
    if authentication_scheme != AUTHENTICATION_SCHEME_BEARER_TOKEN:
        return f"advertises unsupported authentication scheme {authentication_scheme!r}."

    authentication_supported_transports = capabilities.get("authentication_supported_transports")
    if not _is_string_list(authentication_supported_transports):
        return "authentication_supported_transports must be a string list."
    missing_auth_transports = sorted(
        set(REQUIRED_AUTHENTICATION_TRANSPORTS).difference(authentication_supported_transports)
    )
    if missing_auth_transports:
        return (
            "does not support required authentication transports: "
            f"{', '.join(missing_auth_transports)}"
        )

    authentication_query_parameter_name = capabilities.get("authentication_query_parameter_name")
    if authentication_query_parameter_name != ACCESS_TOKEN_QUERY_PARAMETER:
        return (
            "advertises unsupported authentication query parameter "
            f"{authentication_query_parameter_name!r}."
        )

    message_schema_url = capabilities.get("message_schema_url")
    if not isinstance(message_schema_url, str) or not message_schema_url.strip():
        return "message_schema_url must be a non-empty string."

    browser_probe_url = capabilities.get("browser_probe_url")
    if not isinstance(browser_probe_url, str) or not browser_probe_url.strip():
        return "browser_probe_url must be a non-empty string."

    return None


def build_remote_observer_websocket_connect_info(
    *,
    websocket_url: str,
    access_token: str,
    client_name: str,
    capabilities: Mapping[str, Any],
    prefer_authorization_header: bool,
) -> RemoteObserverWebSocketConnectInfo:
    validation_error = validate_remote_observer_capabilities_payload(capabilities)
    if validation_error is not None:
        raise ValueError(validation_error)
    supported_transports = capabilities["authentication_supported_transports"]
    session_url = f"{websocket_url}?client_name={quote(client_name)}"
    if prefer_authorization_header and "authorization_header" in supported_transports:
        return RemoteObserverWebSocketConnectInfo(
            session_url=session_url,
            additional_headers=(("Authorization", f"Bearer {access_token}"),),
        )
    query_parameter_name = str(capabilities["authentication_query_parameter_name"])
    return RemoteObserverWebSocketConnectInfo(
        session_url=(
            f"{session_url}&{quote(query_parameter_name)}={quote(access_token)}"
        )
    )


def _is_string_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)
