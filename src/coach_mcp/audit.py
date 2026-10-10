"""Structured audit logging for tool invocations (Swiss nLPD accountability).

Every MCP tool invocation is recorded as a single-line JSON object on stderr
(AC1/AC6): timestamp, tool name, caller identity, athlete ID, redacted
arguments, duration in milliseconds, outcome status, and the MCP correlation
id. Successful calls are logged at INFO, tool errors at ERROR (AC4), and
authentication failures at WARNING (AC3). Secrets and PII never reach the log:
arguments pass through the #18 redaction layer
(:func:`coach_mcp.security.redact_structure`) before serialization (AC5).

The public hook is :func:`audit_tool_call` — a decorator applied directly below
``@mcp.tool(...)`` so every registered tool (current and future, read or write)
is audited from day one without retrofitting. Write tools from the #82
expansion get full audit coverage by adding the decorator to the tool function.
"""

from __future__ import annotations

import functools
import json
import logging
import sys
import time
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime
from typing import Any, TypeVar, cast

from mcp.server.mcpserver import Context
from pydantic import BaseModel

from coach_mcp.config import settings
from coach_mcp.security import redact_sensitive, redact_structure

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])

#: Logger emitting one JSON line per audit event, stderr only (AC6).
audit_logger = logging.getLogger("coach_mcp.audit")

#: Caller identity recorded until the bearer-token auth layer provides real ones.
ANONYMOUS_CALLER = "anonymous"

#: Prefix of the handled-failure convention: tools return "Error ..." strings.
_ERROR_RESULT_PREFIX = "Error"

if not audit_logger.handlers:
    _handler = logging.StreamHandler(sys.stderr)
    _handler.setFormatter(logging.Formatter("%(message)s"))
    audit_logger.addHandler(_handler)
    audit_logger.setLevel(logging.INFO)
audit_logger.propagate = False


def _utc_timestamp() -> str:
    """Return the current UTC time as ISO 8601 with millisecond precision."""
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def emit_audit(level: int, entry: dict[str, Any]) -> None:
    """Write one audit entry to stderr as a single-line JSON object."""
    audit_logger.log(level, json.dumps(entry, default=str))


def build_audit_entry(
    *,
    tool: str,
    caller: str,
    athlete_id: str | None,
    arguments: dict[str, Any],
    duration_ms: float,
    status: str,
    correlation_id: str | None,
    error: str | None,
) -> dict[str, Any]:
    """Build a ``tool_call`` audit entry with a stable key order.

    The fixed key order keeps the JSON schema stable for log parsers. The
    ``arguments`` mapping is redacted through the #18 redaction layer before
    inclusion (AC5).
    """
    return {
        "timestamp": _utc_timestamp(),
        "event": "tool_call",
        "tool": tool,
        "caller": caller,
        "athlete_id": athlete_id,
        "arguments": redact_structure(arguments),
        "duration_ms": round(duration_ms, 3),
        "status": status,
        "correlation_id": correlation_id,
        "error": error,
    }


def emit_auth_failure(*, caller: str = ANONYMOUS_CALLER, detail: str = "") -> None:
    """Record a rejected authentication attempt at WARNING level (AC3).

    The bearer-token auth layer calls this for every refused credential. The
    detail string is redacted before emission so tokens never reach the log.
    """
    entry: dict[str, Any] = {
        "timestamp": _utc_timestamp(),
        "event": "auth_failure",
        "caller": caller,
        "detail": redact_sensitive(detail) or "",
        "status": "error",
    }
    emit_audit(logging.WARNING, entry)


def _find_ctx(args: tuple[Any, ...], kwargs: Mapping[str, Any]) -> Any:
    """Locate the MCP Context among invocation arguments, if any.

    The SDK invokes tools with keyword arguments (``ctx=...``); direct calls in
    tests may pass the context positionally.
    """
    if "ctx" in kwargs:
        return kwargs["ctx"]
    for value in args:
        if isinstance(value, Context):
            return value
    return None


def _extract_params(args: tuple[Any, ...], kwargs: Mapping[str, Any]) -> Any:
    """Return the invocation's Pydantic input model, if present.

    Tools follow the ``async def tool(params: XInput, ctx: Context)`` convention;
    the Context object and non-model arguments are not invocation arguments and
    are never serialized into the audit record.
    """
    for value in (*args, *kwargs.values()):
        if isinstance(value, BaseModel):
            return value
    return None


def _serialize_arguments(params: Any) -> dict[str, Any]:
    """Serialize the invocation's input model to a JSON-safe mapping."""
    if isinstance(params, BaseModel):
        dumped: dict[str, Any] = params.model_dump(mode="json")
        return dumped
    return {}


def _resolve_caller(ctx: Any) -> str:
    """Resolve the caller identity for an invocation.

    The bearer-token auth layer (upstream issue) will map authenticated tokens
    to caller identities via the request context; until then every invocation
    is attributed to ``anonymous`` (dev mode).
    """
    return ANONYMOUS_CALLER


def _resolve_correlation_id(ctx: Any) -> str | None:
    """Return the MCP request id as the audit correlation id, when available.

    A context without an active request (e.g. bare ``Context()``) yields ``None``
    instead of breaking audit emission.
    """
    try:
        value = ctx.request_id
    except (AttributeError, TypeError, ValueError):
        return None
    if isinstance(value, str) and value:
        return value
    return None


def _resolve_athlete_id(params: Any) -> str | None:
    """Extract the athlete id targeted by the invocation.

    Falls back to the configured default athlete when the tool's input model
    carries no explicit ``athlete_id`` (e.g. activity-scoped tools).
    """
    explicit = getattr(params, "athlete_id", None)
    if explicit:
        return str(explicit)
    return str(settings.intervals_athlete_id)


def _is_error_result(result: Any) -> bool:
    """Detect the codebase's handled-failure convention.

    Tool functions report handled errors (e.g. ``IntervalsAPIError``) by
    returning a redacted message starting with ``Error``; unhandled failures
    propagate as exceptions. Both outcomes are audited as ``status="error"``.
    """
    return isinstance(result, str) and result.startswith(_ERROR_RESULT_PREFIX)


def _emit_tool_call(
    *,
    tool: str,
    args: tuple[Any, ...],
    kwargs: Mapping[str, Any],
    ctx: Any,
    duration_ms: float,
    status: str,
    error: str | None,
) -> None:
    """Build and emit one ``tool_call`` audit entry at the outcome's level."""
    params = _extract_params(args, kwargs)
    entry = build_audit_entry(
        tool=tool,
        caller=_resolve_caller(ctx),
        athlete_id=_resolve_athlete_id(params),
        arguments=_serialize_arguments(params),
        duration_ms=duration_ms,
        status=status,
        correlation_id=_resolve_correlation_id(ctx),
        error=error,
    )
    emit_audit(logging.INFO if status == "success" else logging.ERROR, entry)


def audit_tool_call(func: F) -> F:
    """Emit a structured audit record for every invocation of a tool function.

    Apply directly below ``@mcp.tool(...)`` so the registered tool is the
    audited wrapper::

        @mcp.tool(name="intervals_create_event", annotations=...)
        @audit_tool_call
        async def intervals_create_event(params: CreateEventInput, ctx: Context) -> str:
            ...

    Successful invocations are logged at INFO with ``status="success"``;
    failures — raised exceptions or the handled error-string convention — at
    ERROR with ``status="error"`` (AC4). The decorator never alters the tool's
    return value and audit emission never breaks the tool call.
    """

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        tool_name = func.__name__
        started = time.perf_counter()
        ctx = _find_ctx(args, kwargs)
        try:
            result = await func(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            _emit_tool_call(
                tool=tool_name,
                args=args,
                kwargs=kwargs,
                ctx=ctx,
                duration_ms=(time.perf_counter() - started) * 1000,
                status="error",
                error=f"{type(exc).__name__}: {redact_sensitive(str(exc))}",
            )
            raise
        is_error = _is_error_result(result)
        _emit_tool_call(
            tool=tool_name,
            args=args,
            kwargs=kwargs,
            ctx=ctx,
            duration_ms=(time.perf_counter() - started) * 1000,
            status="error" if is_error else "success",
            error=redact_sensitive(result) if is_error else None,
        )
        return result

    wrapper.__audit_wrapped__ = True  # type: ignore[attr-defined]
    return cast(F, wrapper)
