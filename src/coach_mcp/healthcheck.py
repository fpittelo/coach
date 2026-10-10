"""Transport-aware container healthcheck probe for the coach MCP server.

Used by the image-level Docker HEALTHCHECK so a dead or hung MCP server no
longer reports "running" (issue #75). Exit code contract: 0 = healthy,
1 = unhealthy.

Transport behavior:

- ``stdio``: no HTTP endpoint exists; the server process *is* the container
  process, so a dead server exits the container itself. The probe reports
  healthy (exit 0) while the container is running.
- ``streamable-http``: probes ``GET /mcp`` on the configured host/port.
- ``sse``: probes ``GET /sse`` on the configured host/port.

Any HTTP response (any status code) proves the ASGI server is serving the
MCP endpoint: the MCP transports answer 4xx to unauthenticated GET probes
by design (missing session ID / method not allowed). Connection errors and
timeouts — a killed process or a hung event loop — exit non-zero so Docker
marks the container ``unhealthy``.
"""

import sys

import httpx

from coach_mcp.config import settings

PROBE_TIMEOUT_SECONDS = 5.0
_LOOPBACK_HOST = "127.0.0.1"
_BIND_ALL_HOSTS = frozenset({"0.0.0.0", "::"})


def _probe_host(host: str) -> str:
    """Map bind-all addresses to loopback so the probe dials a dialable target."""
    return _LOOPBACK_HOST if host in _BIND_ALL_HOSTS else host


def resolve_probe_url(transport: str, host: str, port: int) -> str | None:
    """Resolve the HTTP endpoint to probe for the configured transport.

    The transport alias ``streamable_http`` is normalized to
    ``streamable-http`` exactly like ``server.main()`` does. Returns
    ``None`` for ``stdio`` (no HTTP endpoint to probe).
    """
    normalized = transport.replace("_", "-")
    if normalized == "stdio":
        return None
    path = "/sse" if normalized == "sse" else "/mcp"
    return f"http://{_probe_host(host)}:{port}{path}"


def probe(url: str, transport: httpx.BaseTransport | None = None) -> bool:
    """Return True when the MCP endpoint answers with any HTTP response.

    The stream request context returns as soon as response headers arrive;
    the body (an endless SSE stream for ``/sse``) is intentionally never
    consumed, so the probe never hangs on a healthy streaming endpoint.
    """
    try:
        with httpx.Client(timeout=PROBE_TIMEOUT_SECONDS, transport=transport) as client:
            with client.stream("GET", url):
                return True
    except httpx.HTTPError:
        return False


def main() -> int:
    """Healthcheck entrypoint: 0 = healthy, 1 = unhealthy."""
    url = resolve_probe_url(settings.mcp_transport, settings.mcp_host, settings.mcp_port)
    if url is None:
        return 0
    return 0 if probe(url) else 1


if __name__ == "__main__":
    sys.exit(main())
