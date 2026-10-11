"""Tests for bearer-token authentication on the HTTP/SSE transports (issue #61).

Covers the issue #61 acceptance criteria:

- AC2: ``Authorization: Bearer <token>`` is checked on every HTTP request.
- AC3: a valid token is allowed through to the application.
- AC4: a missing or wrong token is rejected with ``401 Unauthorized``.
- AC5: with no token configured the server logs a WARNING and allows all
  requests (unauthenticated dev mode, backward compatible).
- The token comparison is constant-time (``secrets.compare_digest``).
- The token value is never echoed in responses or logs.
- Both the legacy SSE transport (``/sse`` + ``/messages/``) and the
  streamable-HTTP transport (``/mcp``) are protected by the same middleware.
"""

import logging
from typing import Any

import pytest
from starlette.testclient import TestClient

import coach_mcp.auth as auth_module
from coach_mcp.auth import BearerTokenMiddleware
from coach_mcp.server import _build_http_app, mcp, settings

TOKEN = "unit-test-bearer-token"


class DummyApp:
    """Minimal ASGI app recording whether it was reached and answering 200."""

    def __init__(self) -> None:
        self.called = False

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        self.called = True
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send({"type": "http.response.body", "body": b'{"ok": true}'})


@pytest.fixture
def dummy() -> DummyApp:
    return DummyApp()


@pytest.fixture
def client(dummy: DummyApp) -> TestClient:
    return TestClient(BearerTokenMiddleware(dummy, TOKEN))


# ---------------------------------------------------------------------------
# Middleware unit behaviour (AC2/AC3/AC4)
# ---------------------------------------------------------------------------


def test_missing_authorization_header_rejected_401(client: TestClient, dummy: DummyApp) -> None:
    """AC4: a request without an Authorization header is rejected with 401."""
    response = client.get("/sse")
    assert response.status_code == 401
    assert dummy.called is False


def test_wrong_token_rejected_401(client: TestClient, dummy: DummyApp) -> None:
    """AC4: a wrong bearer token is rejected with 401."""
    response = client.get("/sse", headers={"Authorization": f"Bearer wrong-{TOKEN}"})
    assert response.status_code == 401
    assert dummy.called is False


def test_valid_token_allowed(client: TestClient, dummy: DummyApp) -> None:
    """AC3: a request carrying the configured bearer token reaches the app."""
    response = client.get("/sse", headers={"Authorization": f"Bearer {TOKEN}"})
    assert response.status_code == 200
    assert dummy.called is True


def test_non_bearer_scheme_rejected_401(client: TestClient, dummy: DummyApp) -> None:
    """AC4: a non-Bearer credential scheme (e.g. Basic) is rejected."""
    response = client.get("/sse", headers={"Authorization": "Basic dXNlcjpwYXNz"})
    assert response.status_code == 401
    assert dummy.called is False


def test_bearer_scheme_case_insensitive(client: TestClient, dummy: DummyApp) -> None:
    """The auth scheme is case-insensitive per RFC 7235."""
    response = client.get("/sse", headers={"Authorization": f"bearer {TOKEN}"})
    assert response.status_code == 200
    assert dummy.called is True


def test_empty_bearer_credentials_rejected_401(client: TestClient, dummy: DummyApp) -> None:
    """AC4: a bare 'Bearer' header with no credentials is rejected."""
    response = client.get("/sse", headers={"Authorization": "Bearer "})
    assert response.status_code == 401
    assert dummy.called is False


def test_non_http_scope_passes_through(dummy: DummyApp) -> None:
    """Non-HTTP scopes (e.g. lifespan) bypass the bearer check untouched."""
    import asyncio

    async def noop_receive() -> dict[str, Any]:
        return {"type": "lifespan.startup"}

    async def noop_send(message: dict[str, Any]) -> None:
        return None

    scope: dict[str, Any] = {"type": "lifespan"}
    asyncio.run(BearerTokenMiddleware(dummy, TOKEN)(scope, noop_receive, noop_send))
    assert dummy.called is True


# ---------------------------------------------------------------------------
# 401 response shape: challenge header, no token echo
# ---------------------------------------------------------------------------


def test_rejection_sets_www_authenticate_challenge(client: TestClient) -> None:
    """A 401 response carries a WWW-Authenticate: Bearer challenge."""
    response = client.get("/sse")
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_rejection_response_does_not_echo_tokens(client: TestClient, dummy: DummyApp) -> None:
    """Neither the configured token nor the presented one appears in the 401."""
    response = client.get("/sse", headers={"Authorization": f"Bearer wrong-{TOKEN}"})
    assert response.status_code == 401
    assert TOKEN not in response.text
    assert f"wrong-{TOKEN}" not in response.text


def test_rejection_log_does_not_contain_token(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The rejection log records method/path only — never the token value."""
    with caplog.at_level(logging.DEBUG, logger="coach_mcp.auth"):
        client.get("/sse", headers={"Authorization": f"Bearer wrong-{TOKEN}"})
    assert TOKEN not in caplog.text


# ---------------------------------------------------------------------------
# Constant-time comparison
# ---------------------------------------------------------------------------


def test_token_comparison_is_constant_time(
    monkeypatch: pytest.MonkeyPatch, dummy: DummyApp
) -> None:
    """The presented and configured tokens are compared via compare_digest."""
    calls: list[tuple[bytes, bytes]] = []
    real_compare_digest = auth_module.compare_digest

    def spy(a: bytes | str, b: bytes | str) -> bool:
        calls.append((a, b))  # type: ignore[arg-type]
        return real_compare_digest(a, b)

    monkeypatch.setattr(auth_module, "compare_digest", spy)
    guarded = TestClient(BearerTokenMiddleware(dummy, TOKEN))
    guarded.get("/sse", headers={"Authorization": f"Bearer {TOKEN}"})
    assert calls == [(TOKEN.encode(), TOKEN.encode())]


# ---------------------------------------------------------------------------
# Transport wiring (SSE + streamable-http) and dev mode (AC5)
# ---------------------------------------------------------------------------


@pytest.fixture
def _auth_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "coach_mcp_auth_token", TOKEN)


@pytest.fixture
def _no_auth_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "coach_mcp_auth_token", "")


def test_sse_app_rejects_missing_token(_auth_token: None) -> None:
    """AC2/AC4: the real SSE app rejects an unauthenticated /sse request."""
    app = _build_http_app("sse")
    with TestClient(app) as http:
        assert http.get("/sse").status_code == 401


def test_sse_app_rejects_wrong_token(_auth_token: None) -> None:
    """AC2/AC4: the real SSE app rejects a wrong bearer token."""
    app = _build_http_app("sse")
    with TestClient(app) as http:
        response = http.get("/sse", headers={"Authorization": "Bearer nope"})
        assert response.status_code == 401


def test_streamable_app_rejects_missing_token(_auth_token: None) -> None:
    """AC2/AC4: the real streamable-HTTP app rejects an unauthenticated /mcp."""
    app = _build_http_app("streamable-http")
    with TestClient(app) as http:
        assert http.post("/mcp").status_code == 401


def test_streamable_app_rejects_wrong_token(_auth_token: None) -> None:
    """AC2/AC4: the real streamable-HTTP app rejects a wrong bearer token."""
    app = _build_http_app("streamable-http")
    with TestClient(app) as http:
        response = http.post("/mcp", headers={"Authorization": "Bearer nope"})
        assert response.status_code == 401


def test_streamable_app_valid_token_passes_auth_layer(_auth_token: None) -> None:
    """AC3: a valid token crosses the auth layer (response is not a 401)."""
    app = _build_http_app("streamable-http")
    with TestClient(app) as http:
        response = http.post("/mcp", headers={"Authorization": f"Bearer {TOKEN}"})
        assert response.status_code != 401


def test_build_http_app_wraps_when_token_set(
    _auth_token: None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """With a token configured, the HTTP app is wrapped by the middleware."""
    with caplog.at_level(logging.INFO, logger="coach_mcp"):
        app = _build_http_app("sse")
    assert isinstance(app, BearerTokenMiddleware)
    assert "Bearer token authentication enabled" in caplog.text


def test_build_http_app_dev_mode_unwrapped_with_warning(
    _no_auth_token: None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """AC5: without a token the app is unwrapped and a WARNING is logged."""
    with caplog.at_level(logging.WARNING, logger="coach_mcp"):
        app = _build_http_app("streamable-http")
    assert not isinstance(app, BearerTokenMiddleware)
    assert "unauthenticated dev mode" in caplog.text
    assert any(record.levelno == logging.WARNING for record in caplog.records)


def test_main_serves_wrapped_app_for_sse(
    _auth_token: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """main() serves the bearer-wrapped SSE app through uvicorn."""
    served: dict[str, Any] = {}

    def fake_run(app: Any, **kwargs: Any) -> None:
        served["app"] = app
        served.update(kwargs)

    monkeypatch.setattr(settings, "mcp_transport", "sse")
    monkeypatch.setattr("coach_mcp.server.uvicorn.run", fake_run)
    from coach_mcp.server import main

    main()
    assert isinstance(served["app"], BearerTokenMiddleware)
    assert served["host"] == settings.mcp_host
    assert served["port"] == settings.mcp_port


def test_main_stdio_mode_never_builds_http_app(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """stdio transport is untouched by the HTTP auth layer (backward compat)."""
    monkeypatch.setattr(settings, "mcp_transport", "stdio")
    run_calls: list[dict[str, Any]] = []

    def fake_mcp_run(**kwargs: Any) -> None:
        run_calls.append(kwargs)

    monkeypatch.setattr(mcp, "run", fake_mcp_run)
    from coach_mcp.server import main

    main()
    assert run_calls == [{"transport": "stdio"}]
