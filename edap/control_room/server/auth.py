from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from starlette.requests import Request
from starlette.websockets import WebSocket


ACCESS_TOKEN_QUERY_PARAMETER = "access_token"


@dataclass(frozen=True)
class AuthDescription:
    authentication_required: bool
    authentication_scheme: str
    supported_transports: tuple[str, ...]
    query_parameter_name: str | None = None


class ObserverServerAuth(Protocol):
    def describe(self) -> AuthDescription: ...

    def is_http_request_authorized(self, request: Request) -> bool: ...

    def is_websocket_authorized(self, websocket: WebSocket) -> bool: ...


@dataclass(frozen=True)
class SharedAccessTokenAuth:
    access_token: str

    def describe(self) -> AuthDescription:
        return AuthDescription(
            authentication_required=True,
            authentication_scheme="bearer_token",
            supported_transports=("authorization_header", "query_parameter"),
            query_parameter_name=ACCESS_TOKEN_QUERY_PARAMETER,
        )

    def is_http_request_authorized(self, request: Request) -> bool:
        return _is_token_authorized(
            expected_token=self.access_token,
            authorization_header=request.headers.get("authorization"),
            query_token=request.query_params.get(ACCESS_TOKEN_QUERY_PARAMETER),
        )

    def is_websocket_authorized(self, websocket: WebSocket) -> bool:
        return _is_token_authorized(
            expected_token=self.access_token,
            authorization_header=websocket.headers.get("authorization"),
            query_token=websocket.query_params.get(ACCESS_TOKEN_QUERY_PARAMETER),
        )


def _is_token_authorized(
    *,
    expected_token: str,
    authorization_header: str | None,
    query_token: str | None,
) -> bool:
    bearer_token = _parse_bearer_token(authorization_header)
    if bearer_token is not None:
        return bearer_token == expected_token
    if query_token is not None:
        return query_token == expected_token
    return False


def _parse_bearer_token(authorization_header: str | None) -> str | None:
    if authorization_header is None:
        return None
    scheme, _, token = authorization_header.partition(" ")
    if scheme.lower() != "bearer":
        return None
    stripped = token.strip()
    return stripped or None
