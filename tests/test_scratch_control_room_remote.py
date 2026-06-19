from __future__ import annotations

import unittest

from edap.control_room.client.target import ObserverServerTarget
from edap.control_room.protocol import (
    ACCESS_TOKEN_QUERY_PARAMETER,
    AUTHENTICATION_SCHEME_BEARER_TOKEN,
    REQUIRED_AUTHENTICATION_TRANSPORTS,
    build_remote_observer_capabilities_payload,
)
from tools.scratch.scratch_control_room_remote import _session_url_from_capabilities


def _target() -> ObserverServerTarget:
    return ObserverServerTarget(
        host="bridge.local",
        port=8765,
        http_base_url="http://bridge.local:8765",
        websocket_url="ws://bridge.local:8765/session",
    )


def _capabilities() -> dict[str, object]:
    return build_remote_observer_capabilities_payload(
        capability_names=["remote_observer"],
        server_version="1.2.3",
        authentication_required=True,
        authentication_scheme=AUTHENTICATION_SCHEME_BEARER_TOKEN,
        authentication_supported_transports=REQUIRED_AUTHENTICATION_TRANSPORTS,
        authentication_query_parameter_name=ACCESS_TOKEN_QUERY_PARAMETER,
        message_schema_url="/schema/control_room_message.json",
        browser_probe_url="/browser-probe",
    )


class ScratchControlRoomRemoteTests(unittest.TestCase):
    def test_session_url_uses_current_capability_contract(self) -> None:
        url = _session_url_from_capabilities(
            _target(),
            token="secret token",
            client_name="browser probe",
            capabilities=_capabilities(),
        )

        self.assertEqual(
            url,
            "ws://bridge.local:8765/session?client_name=browser%20probe",
        )

    def test_session_url_rejects_missing_query_parameter_transport(self) -> None:
        capabilities = _capabilities()
        capabilities["authentication_supported_transports"] = ["authorization_header"]

        with self.assertRaises(SystemExit) as ctx:
            _session_url_from_capabilities(
                _target(),
                token="secret-token",
                client_name="scratch-probe",
                capabilities=capabilities,
            )

        self.assertIn(
            "does not support required authentication transports: query_parameter",
            str(ctx.exception),
        )


if __name__ == "__main__":
    unittest.main()
