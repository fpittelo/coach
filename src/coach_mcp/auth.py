"""Bearer-token authentication for the coach-mcp HTTP transports (issue #61).

A single shared-token check protects both HTTP transports uniformly:

* legacy SSE — ``GET /sse`` and ``POST /messages/``;
* streamable HTTP — ``POST /mcp``.

When ``COACH_MCP_AUTH_TOKEN`` is configured, every HTTP request must carry
``Authorization: Bearer <token>``; anything else is rejected with ``401`` and
a ``WWW-Authenticate: Bearer`` challenge. The comparison is constant-time
(``secrets.compare_digest``) and the token value is never echoed in responses
or logs. With no token configured the middleware is not installed at all and
the server logs a startup warning (unauthenticated dev mode, backward
compatible with stdio local usage).

The middleware is pure ASGI (no Starlette request objects) so it can wrap the
transport apps produced by the MCP SDK without coupling to their internals.
"""

import logging
import secrets

from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger("coach_mcp.auth")

_UNAUTHORIZED_BODY = b'{"error":"unauthorized"}'
_WWW_AUTHENTICATE_VALUE = b"Bearer"

compare_digest = secrets.compare_digest


class BearerTokenMiddleware:
    """ASGI middleware enforcing a shared bearer token on every HTTP request.

    Args:
        app: The ASGI application to guard (the SSE or streamable-HTTP app).
        token: The configured shared bearer token. Callers must only install
            this middleware when a non-empty token is configured; an empty
            token would reject every request.
    """

    def __init__(self, app: ASGIApp, token: str) -> None:
        """Store the guarded app and the shared token (``settings.coach_mcp_auth_token``)."""
        self.app = app
        self._token = token

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Reject non-bearer HTTP requests; pass everything else through."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        if not self._is_authorized(scope):
            logger.warning(
                "Rejected unauthorized request: %s %s",
                scope.get("method", "-"),
                scope.get("path", "-"),
            )
            await self._send_unauthorized(send)
            return
        await self.app(scope, receive, send)

    def _is_authorized(self, scope: Scope) -> bool:
        """Check the Authorization header against the configured token."""
        authorization = self._get_authorization_header(scope)
        if authorization is None:
            return False
        scheme, _, credentials = authorization.partition(" ")
        if scheme.lower() != "bearer":
            return False
        credentials = credentials.strip()
        if not credentials:
            return False
        return compare_digest(credentials.encode("utf-8"), self._token.encode("utf-8"))

    @staticmethod
    def _get_authorization_header(scope: Scope) -> str | None:
        """Extract the Authorization header value from the raw ASGI scope."""
        headers: list[tuple[bytes, bytes]] = scope.get("headers") or []
        for key, value in headers:
            if key.lower() == b"authorization":
                return value.decode("latin-1")
        return None

    @staticmethod
    async def _send_unauthorized(send: Send) -> None:
        """Send a 401 response with a Bearer challenge and no token echo."""
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(_UNAUTHORIZED_BODY)).encode("ascii")),
                    (b"www-authenticate", _WWW_AUTHENTICATE_VALUE),
                ],
            }
        )
        await send({"type": "http.response.body", "body": _UNAUTHORIZED_BODY})
