from __future__ import annotations

import json
import unittest
from pathlib import Path

from edap.control_room.server.app import SUPPORTED_MESSAGE_TYPES


_SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent / "docs" / "schemas" / "control_room_message.schema.json"
)


class ControlRoomMessageSchemaTests(unittest.TestCase):
    def test_schema_message_types_match_server_surface(self) -> None:
        schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))

        self.assertEqual(schema["properties"]["message_type"]["enum"], SUPPORTED_MESSAGE_TYPES)

        schema_message_types = {
            block["if"]["properties"]["message_type"]["const"]
            for block in schema["allOf"]
        }
        self.assertEqual(schema_message_types, set(SUPPORTED_MESSAGE_TYPES))

    def test_active_operator_change_payload_allows_no_active_operator(self) -> None:
        schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
        payload = schema["$defs"]["event_active_operator_changed_payload"]["properties"]

        self.assertEqual(
            payload["active_operator_session_id"]["type"],
            ["string", "null"],
        )
        self.assertEqual(
            payload["active_operator_client_name"]["type"],
            ["string", "null"],
        )

    def test_capabilities_payload_schema_includes_runtime_auth_and_schema_fields(self) -> None:
        schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
        payload = schema["$defs"]["response_capabilities_payload"]

        self.assertEqual(
            payload["required"],
            [
                "capability_names",
                "supported_client_roles",
                "supported_message_types",
                "supported_command_message_types",
                "supported_event_message_types",
                "supported_response_message_types",
                "minimum_client_version",
                "server_version",
                "message_schema_url",
                "browser_probe_url",
                "authentication_required",
                "authentication_scheme",
                "authentication_supported_transports",
                "authentication_query_parameter_name",
            ],
        )


if __name__ == "__main__":
    unittest.main()
