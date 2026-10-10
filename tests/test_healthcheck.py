"""Tests for the transport-aware container healthcheck probe (issue #75)."""

import httpx

from coach_mcp import healthcheck
from coach_mcp.config import settings

# ---------------------------------------------------------------------------
# resolve_probe_url: transport -> probe endpoint mapping
# ---------------------------------------------------------------------------


def test_resolve_probe_url_stdio_returns_none():
    """stdio containers have no HTTP endpoint; nothing to probe."""
    assert healthcheck.resolve_probe_url("stdio", "0.0.0.0", 8000) is None


def test_resolve_probe_url_streamable_http_probes_mcp_endpoint():
    """streamable-http probes the /mcp streamable HTTP endpoint."""
    url = healthcheck.resolve_probe_url("streamable-http", "0.0.0.0", 8000)
    assert url == "http://127.0.0.1:8000/mcp"


def test_resolve_probe_url_streamable_http_alias_normalized():
    """The 'streamable_http' env alias is normalized like server.main() does."""
    url = healthcheck.resolve_probe_url("streamable_http", "0.0.0.0", 8000)
    assert url == "http://127.0.0.1:8000/mcp"


def test_resolve_probe_url_sse_probes_sse_endpoint():
    """sse probes the /sse endpoint (coach-web sidecar contract)."""
    url = healthcheck.resolve_probe_url("sse", "0.0.0.0", 8000)
    assert url == "http://127.0.0.1:8000/sse"


def test_resolve_probe_url_bind_all_host_mapped_to_loopback():
    """A bind-all host is not dialable; the probe targets loopback instead."""
    url = healthcheck.resolve_probe_url("streamable-http", "0.0.0.0", 9000)
    assert url == "http://127.0.0.1:9000/mcp"


def test_resolve_probe_url_explicit_host_preserved():
    """An explicitly configured host is probed as-is."""
    url = healthcheck.resolve_probe_url("streamable-http", "192.168.1.10", 8000)
    assert url == "http://192.168.1.10:8000/mcp"


# ---------------------------------------------------------------------------
# probe: any HTTP response = healthy; connection errors/timeouts = unhealthy
# ---------------------------------------------------------------------------


def test_probe_healthy_on_http_response():
    """Any HTTP response (even 4xx) proves the MCP server is serving."""
    seen_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_urls.append(str(request.url))
        return httpx.Response(400, text="Bad Request: Missing session ID")

    result = healthcheck.probe("http://127.0.0.1:8000/mcp", transport=httpx.MockTransport(handler))

    assert result is True
    assert seen_urls == ["http://127.0.0.1:8000/mcp"]


def test_probe_healthy_on_sse_stream():
    """A streaming SSE response (endless body) is healthy, never hangs."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=iter([b"event: endpoint\r\n\r\n"]),
        )

    result = healthcheck.probe("http://127.0.0.1:8000/sse", transport=httpx.MockTransport(handler))

    assert result is True


def test_probe_unhealthy_on_connection_error():
    """A dead server (connection refused) is unhealthy."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    result = healthcheck.probe("http://127.0.0.1:8000/mcp", transport=httpx.MockTransport(handler))

    assert result is False


def test_probe_unhealthy_on_timeout():
    """A hung server (no response within the probe timeout) is unhealthy."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out")

    result = healthcheck.probe("http://127.0.0.1:8000/mcp", transport=httpx.MockTransport(handler))

    assert result is False


# ---------------------------------------------------------------------------
# main(): wiring of settings -> probe -> exit code
# ---------------------------------------------------------------------------


def test_main_stdio_returns_zero_without_probing(monkeypatch):
    """stdio: healthy exit code, no HTTP probe is attempted."""
    monkeypatch.setattr(settings, "mcp_transport", "stdio")
    calls: list[str] = []

    def fail_probe(url: str, transport: httpx.BaseTransport | None = None) -> bool:
        calls.append(url)
        return False

    monkeypatch.setattr(healthcheck, "probe", fail_probe)

    assert healthcheck.main() == 0
    assert calls == []


def test_main_streamable_http_healthy(monkeypatch):
    """streamable-http: probes the resolved /mcp URL and exits 0 on success."""
    monkeypatch.setattr(settings, "mcp_transport", "streamable-http")
    monkeypatch.setattr(settings, "mcp_host", "0.0.0.0")
    monkeypatch.setattr(settings, "mcp_port", 8000)
    seen_urls: list[str] = []

    def fake_probe(url: str, transport: httpx.BaseTransport | None = None) -> bool:
        seen_urls.append(url)
        return True

    monkeypatch.setattr(healthcheck, "probe", fake_probe)

    assert healthcheck.main() == 0
    assert seen_urls == ["http://127.0.0.1:8000/mcp"]


def test_main_streamable_http_unhealthy(monkeypatch):
    """streamable-http: exits 1 when the endpoint does not answer."""
    monkeypatch.setattr(settings, "mcp_transport", "streamable-http")
    monkeypatch.setattr(settings, "mcp_host", "0.0.0.0")
    monkeypatch.setattr(settings, "mcp_port", 8000)

    def dead_probe(url: str, transport: httpx.BaseTransport | None = None) -> bool:
        return False

    monkeypatch.setattr(healthcheck, "probe", dead_probe)

    assert healthcheck.main() == 1


def test_main_sse_healthy(monkeypatch):
    """sse: probes the resolved /sse URL and exits 0 on success."""
    monkeypatch.setattr(settings, "mcp_transport", "sse")
    monkeypatch.setattr(settings, "mcp_host", "0.0.0.0")
    monkeypatch.setattr(settings, "mcp_port", 8000)
    seen_urls: list[str] = []

    def fake_probe(url: str, transport: httpx.BaseTransport | None = None) -> bool:
        seen_urls.append(url)
        return True

    monkeypatch.setattr(healthcheck, "probe", fake_probe)

    assert healthcheck.main() == 0
    assert seen_urls == ["http://127.0.0.1:8000/sse"]
