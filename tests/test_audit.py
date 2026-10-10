"""Tests for structured audit logging of tool invocations (#64, Swiss nLPD).

Covers the acceptance criteria of issue #64:

* AC1/AC2 — every tool invocation emits a structured JSON audit record on
  stderr with timestamp, tool name, caller identity, athlete ID, redacted
  arguments, duration_ms, and status.
* AC3 — authentication failures are logged at WARNING level.
* AC4 — tool errors (raised exceptions and the handled error-string
  convention) are logged at ERROR level.
* AC5 — no secrets (API keys, tokens, email PII) appear in audit output.
* AC6 — stdout stays clean; audit records go to stderr only.
* AC8 — tests verify audit log format, redaction, and stderr-only output.
"""

import asyncio
import io
import json
import logging
import sys
from collections.abc import Generator
from contextlib import redirect_stdout
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel

from coach_mcp.audit import audit_logger, audit_tool_call, emit_auth_failure
from coach_mcp.config import settings
from coach_mcp.models import (
    GetActivityInput,
    GetAthleteProfileInput,
    RecordWellnessBulkInput,
    WellnessRecordItem,
)

# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

#: Exact key set of a ``tool_call`` audit entry (schema stability contract).
AUDIT_ENTRY_KEYS = {
    "timestamp",
    "event",
    "tool",
    "caller",
    "athlete_id",
    "arguments",
    "duration_ms",
    "status",
    "correlation_id",
    "error",
}


class _AuditParams(BaseModel):
    """Minimal input model for audit decorator tests."""

    athlete_id: str | None = None
    description: str = ""


class _CaptureHandler(logging.Handler):
    """Logging handler capturing raw LogRecords for assertions."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.fixture
def audit_records() -> Generator[list[logging.LogRecord], None, None]:
    """Capture audit log records emitted during a test."""
    handler = _CaptureHandler()
    audit_logger.addHandler(handler)
    try:
        yield handler.records
    finally:
        audit_logger.removeHandler(handler)


def _entries(records: list[logging.LogRecord]) -> list[dict[str, object]]:
    """Parse captured audit records into JSON entries."""
    return [json.loads(record.getMessage()) for record in records]


# ---------------------------------------------------------------------------
# AC1/AC2 — success invocations emit a complete structured record
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_success_invocation_emits_info_audit_entry(audit_records):
    """A successful tool call emits exactly one INFO-level audit entry."""

    @audit_tool_call
    async def _success_tool(params: _AuditParams, ctx: MagicMock) -> str:
        return "all good"

    result = await _success_tool(
        _AuditParams(athlete_id="i42", description="hard intervals"), MagicMock()
    )

    assert result == "all good"
    assert len(audit_records) == 1
    record = audit_records[0]
    assert record.levelno == logging.INFO
    entry = json.loads(record.getMessage())
    assert entry["event"] == "tool_call"
    assert entry["tool"] == "_success_tool"
    assert entry["status"] == "success"
    assert entry["athlete_id"] == "i42"
    assert entry["arguments"]["description"] == "hard intervals"
    assert entry["error"] is None


def test_audit_entry_schema_is_stable(audit_records):
    """Every audit entry has the exact documented key set and value types."""

    @audit_tool_call
    async def _schema_tool(params: _AuditParams, ctx: MagicMock) -> str:
        return "ok"

    asyncio.run(_schema_tool(_AuditParams(athlete_id="0"), MagicMock()))

    assert len(audit_records) == 1
    entry = json.loads(audit_records[0].getMessage())
    assert set(entry.keys()) == AUDIT_ENTRY_KEYS
    assert isinstance(entry["timestamp"], str)
    # ISO 8601 UTC timestamp with Z suffix, parseable.
    assert entry["timestamp"].endswith("Z")
    parsed = datetime.fromisoformat(entry["timestamp"])
    assert parsed.tzinfo is not None
    assert isinstance(entry["event"], str)
    assert isinstance(entry["tool"], str)
    assert isinstance(entry["caller"], str)
    assert isinstance(entry["arguments"], dict)
    assert isinstance(entry["duration_ms"], (int, float))
    assert entry["duration_ms"] >= 0
    assert isinstance(entry["status"], str)
    assert entry["error"] is None


@pytest.mark.asyncio
async def test_audit_entry_uses_iso8601_utc_millisecond_timestamp(audit_records):
    """The timestamp is UTC ISO 8601 with millisecond precision and Z suffix."""

    @audit_tool_call
    async def _timestamp_tool(params: _AuditParams, ctx: MagicMock) -> str:
        return "ok"

    await _timestamp_tool(_AuditParams(), MagicMock())

    entry = _entries(audit_records)[0]
    timestamp = str(entry["timestamp"])
    assert timestamp.endswith("Z")
    # Millisecond precision: exactly 3 fractional digits.
    fractional = timestamp.split(".")[1].rstrip("Z")
    assert len(fractional) == 3
    parsed = datetime.fromisoformat(timestamp)
    assert parsed.utcoffset() is not None


# ---------------------------------------------------------------------------
# AC4 — tool errors are logged at ERROR level
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_raised_exception_logged_at_error_and_reraised(audit_records):
    """An unhandled tool exception is audited as error and re-raised."""

    @audit_tool_call
    async def _failing_tool(params: _AuditParams, ctx: MagicMock) -> str:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        await _failing_tool(_AuditParams(athlete_id="0"), MagicMock())

    assert len(audit_records) == 1
    record = audit_records[0]
    assert record.levelno == logging.ERROR
    entry = json.loads(record.getMessage())
    assert entry["status"] == "error"
    assert "RuntimeError" in str(entry["error"])


@pytest.mark.asyncio
async def test_error_string_result_logged_at_error(audit_records):
    """The handled error-string convention ('Error ...') is audited as error."""

    @audit_tool_call
    async def _error_string_tool(params: _AuditParams, ctx: MagicMock) -> str:
        return "Error fetching wellness: 401 Unauthorized"

    result = await _error_string_tool(_AuditParams(athlete_id="0"), MagicMock())

    assert result.startswith("Error")
    assert len(audit_records) == 1
    assert audit_records[0].levelno == logging.ERROR
    entry = json.loads(audit_records[0].getMessage())
    assert entry["status"] == "error"
    assert "401" in str(entry["error"])


# ---------------------------------------------------------------------------
# AC3 — auth failures are logged at WARNING level
# ---------------------------------------------------------------------------


def test_auth_failure_logged_at_warning_with_redaction(audit_records):
    """emit_auth_failure records a WARNING-level auth_failure event."""
    emit_auth_failure(caller="coach-web", detail="rejected token Bearer abc.def.ghi")

    assert len(audit_records) == 1
    record = audit_records[0]
    assert record.levelno == logging.WARNING
    entry = json.loads(record.getMessage())
    assert entry["event"] == "auth_failure"
    assert entry["caller"] == "coach-web"
    assert entry["status"] == "error"
    assert "abc.def.ghi" not in str(entry["detail"])
    assert "[REDACTED]" in str(entry["detail"])


# ---------------------------------------------------------------------------
# AC5 — no secrets in audit output
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_secrets_never_appear_in_audit_output(audit_records):
    """Injected fake secrets in tool arguments never reach the audit record."""

    @audit_tool_call
    async def _secret_tool(params: _AuditParams, ctx: MagicMock) -> str:
        return "ok"

    payload = "api_key=sk-fake-123456 contact dev@example.com " "Bearer zzz.yyy.xxx-999"
    await _secret_tool(_AuditParams(athlete_id="0", description=payload), MagicMock())

    output = "\n".join(record.getMessage() for record in audit_records)
    assert "sk-fake-123456" not in output
    assert "dev@example.com" not in output
    assert "zzz.yyy.xxx-999" not in output
    assert "[REDACTED" in output


@pytest.mark.asyncio
async def test_nested_payload_secrets_redacted_end_to_end(audit_records):
    """Secrets inside nested model structures (bulk wellness records) are redacted."""

    @audit_tool_call
    async def _bulk_tool(params: RecordWellnessBulkInput, ctx: MagicMock) -> str:
        return "ok"

    params = RecordWellnessBulkInput(
        records=[
            WellnessRecordItem(
                date="2026-10-10",
                comments="reset api_key=sk-nested-9876 please",
            )
        ],
        athlete_id="0",
    )
    await _bulk_tool(params, MagicMock())

    entry = _entries(audit_records)[0]
    arguments = entry["arguments"]
    assert isinstance(arguments, dict)
    nested_comments = arguments["records"][0]["comments"]
    assert "sk-nested-9876" not in str(nested_comments)
    assert "[REDACTED]" in str(nested_comments)


@pytest.mark.asyncio
async def test_json_in_string_payload_secret_never_reaches_audit(audit_records):
    """Secrets inside JSON-in-string arguments never reach the audit record (PR #88 F1)."""

    @audit_tool_call
    async def _json_tool(params: _AuditParams, ctx: MagicMock) -> str:
        return "ok"

    await _json_tool(
        _AuditParams(athlete_id="0", description='{"api_key": "sk-e2e-1"}'),
        MagicMock(),
    )

    output = "\n".join(record.getMessage() for record in audit_records)
    assert "sk-e2e-1" not in output
    assert "[REDACTED]" in output


@pytest.mark.asyncio
async def test_session_comment_secret_never_reaches_audit(audit_records, monkeypatch):
    """A secret embedded in the session-comment payload never reaches the
    emitted audit record (#85 AC4, pattern of the #88 redaction tests)."""
    from coach_mcp.models import IcuAddSessionCommentInput
    from coach_mcp.server import icu_add_session_comment

    monkeypatch.setattr(settings, "intervals_athlete_id", "0")

    mock_client = MagicMock()
    mock_client.add_activity_message = AsyncMock(return_value={"id": "m1"})
    ctx = MagicMock()
    ctx.request_context.lifespan_state = {"client": mock_client}

    params = IcuAddSessionCommentInput(
        activity_id="i123",
        comment="Debrief done. Rotate api_key=sk-fake-e2e-9876 and email dev@example.com",
        confirmed=True,
    )
    result = await icu_add_session_comment(params, ctx)

    assert result.startswith("Successfully posted session comment")
    assert len(audit_records) == 1
    record = audit_records[0]
    assert record.levelno == logging.INFO
    entry = json.loads(record.getMessage())
    assert entry["event"] == "tool_call"
    assert entry["tool"] == "icu_add_session_comment"
    assert entry["status"] == "success"
    arguments = entry["arguments"]
    assert isinstance(arguments, dict)
    assert arguments["activity_id"] == "i123"
    assert arguments["confirmed"] is True
    output = record.getMessage()
    assert "sk-fake-e2e-9876" not in output
    assert "dev@example.com" not in output
    assert "[REDACTED" in output


@pytest.mark.asyncio
async def test_session_comment_unconfirmed_rejection_audited_at_error(audit_records, monkeypatch):
    """A confirmation-gate rejection is audited as a failed write (ERROR level)."""
    from coach_mcp.models import IcuAddSessionCommentInput
    from coach_mcp.server import icu_add_session_comment

    monkeypatch.setattr(settings, "intervals_athlete_id", "0")

    mock_client = MagicMock()
    mock_client.add_activity_message = AsyncMock()
    ctx = MagicMock()
    ctx.request_context.lifespan_state = {"client": mock_client}

    params = IcuAddSessionCommentInput(activity_id="i123", comment="Great debrief.")
    result = await icu_add_session_comment(params, ctx)

    assert result.startswith("Error")
    mock_client.add_activity_message.assert_not_awaited()
    assert len(audit_records) == 1
    record = audit_records[0]
    assert record.levelno == logging.ERROR
    entry = json.loads(record.getMessage())
    assert entry["status"] == "error"
    assert entry["tool"] == "icu_add_session_comment"


# ---------------------------------------------------------------------------
# AC6 — stderr only, stdout stays clean
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_writes_to_stderr_and_stdout_stays_clean(audit_records):
    """Audit records go to stderr; nothing is written to stdout."""

    @audit_tool_call
    async def _stream_tool(params: _AuditParams, ctx: MagicMock) -> str:
        return "ok"

    stdout_buffer = io.StringIO()
    with redirect_stdout(stdout_buffer):
        await _stream_tool(_AuditParams(), MagicMock())

    assert stdout_buffer.getvalue() == ""
    assert len(audit_records) == 1
    streams = [getattr(handler, "stream", None) for handler in audit_logger.handlers]
    assert sys.stderr in streams
    # Audit records must not propagate to the human-readable coach_mcp logger.
    assert audit_logger.propagate is False


# ---------------------------------------------------------------------------
# Caller identity, athlete ID, correlation id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_caller_is_anonymous_before_auth_layer_exists(audit_records):
    """Caller identity defaults to 'anonymous' until bearer-token auth lands."""

    @audit_tool_call
    async def _caller_tool(params: _AuditParams, ctx: MagicMock) -> str:
        return "ok"

    await _caller_tool(_AuditParams(), MagicMock())

    entry = _entries(audit_records)[0]
    assert entry["caller"] == "anonymous"


@pytest.mark.asyncio
async def test_athlete_id_falls_back_to_settings(audit_records, monkeypatch):
    """Tools without an athlete_id argument audit the configured default athlete."""
    monkeypatch.setattr(settings, "intervals_athlete_id", "i777")

    @audit_tool_call
    async def _no_athlete_tool(params: GetActivityInput, ctx: MagicMock) -> str:
        return "ok"

    await _no_athlete_tool(GetActivityInput(activity_id="a1"), MagicMock())

    entry = _entries(audit_records)[0]
    assert entry["athlete_id"] == "i777"


@pytest.mark.asyncio
async def test_correlation_id_from_context_request_id(audit_records):
    """The MCP request id is recorded as the audit correlation id."""

    @audit_tool_call
    async def _corr_tool(params: _AuditParams, ctx: MagicMock) -> str:
        return "ok"

    ctx = MagicMock()
    ctx.request_id = "req-42"
    await _corr_tool(_AuditParams(), ctx=ctx)

    entry = _entries(audit_records)[0]
    assert entry["correlation_id"] == "req-42"


@pytest.mark.asyncio
async def test_correlation_id_absent_without_request_context(audit_records):
    """A context without a request id yields a null correlation id."""

    @audit_tool_call
    async def _no_corr_tool(params: _AuditParams, ctx) -> str:
        return "ok"

    await _no_corr_tool(_AuditParams(), None)

    entry = _entries(audit_records)[0]
    assert entry["correlation_id"] is None


@pytest.mark.asyncio
async def test_correlation_id_none_when_request_id_is_not_a_string(audit_records):
    """A non-string request id yields a null correlation id."""

    @audit_tool_call
    async def _int_corr_tool(params: _AuditParams, ctx: MagicMock) -> str:
        return "ok"

    ctx = MagicMock()
    ctx.request_id = None
    await _int_corr_tool(_AuditParams(), ctx=ctx)

    entry = _entries(audit_records)[0]
    assert entry["correlation_id"] is None


@pytest.mark.asyncio
async def test_real_mcp_context_without_request_is_tolerated(audit_records):
    """A bare real Context (no active request) must not break audit emission."""
    from mcp.server.mcpserver import Context

    @audit_tool_call
    async def _bare_ctx_tool(params: _AuditParams, ctx: Context) -> str:
        return "ok"

    result = await _bare_ctx_tool(_AuditParams(), Context())

    assert result == "ok"
    entry = _entries(audit_records)[0]
    assert entry["correlation_id"] is None
    assert entry["status"] == "success"


@pytest.mark.asyncio
async def test_invocation_without_params_model_audits_empty_arguments(audit_records):
    """A tool invoked without a Pydantic params model audits empty arguments."""

    @audit_tool_call
    async def _ctx_only_tool(ctx: MagicMock) -> str:
        return "ok"

    result = await _ctx_only_tool(MagicMock())

    assert result == "ok"
    entry = _entries(audit_records)[0]
    assert entry["arguments"] == {}
    assert entry["status"] == "success"


# ---------------------------------------------------------------------------
# Concurrency — isolation under asyncio
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_concurrent_invocations_emit_isolated_entries(audit_records):
    """Concurrent tool calls each emit their own entry with their own arguments."""

    @audit_tool_call
    async def _concurrent_tool(params: _AuditParams, ctx: MagicMock) -> str:
        await asyncio.sleep(0.001)
        return f"done {params.athlete_id}"

    inputs = [
        _AuditParams(athlete_id=f"i{idx:03d}", description=f"payload {idx}") for idx in range(20)
    ]
    results = await asyncio.gather(*(_concurrent_tool(p, MagicMock()) for p in inputs))

    assert results == [f"done i{idx:03d}" for idx in range(20)]
    entries = _entries(audit_records)
    assert len(entries) == 20
    by_athlete = {}
    for entry in entries:
        arguments = entry["arguments"]
        assert isinstance(arguments, dict)
        by_athlete[str(arguments["athlete_id"])] = str(arguments["description"])
        assert entry["status"] == "success"
        assert entry["event"] == "tool_call"
    # No cross-contamination between concurrent invocations.
    assert by_athlete == {f"i{idx:03d}": f"payload {idx}" for idx in range(20)}


# ---------------------------------------------------------------------------
# Decorator hygiene
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_decorator_preserves_metadata_and_return(audit_records):
    """The audited wrapper preserves the tool's name, docstring, and result."""

    @audit_tool_call
    async def _documented_tool(params: _AuditParams, ctx: MagicMock) -> str:
        """Docstring preserved."""
        return "payload"

    assert _documented_tool.__name__ == "_documented_tool"
    assert _documented_tool.__doc__ == "Docstring preserved."
    result = await _documented_tool(_AuditParams(), MagicMock())
    assert result == "payload"


def test_all_registered_server_tools_are_audited():
    """Every tool registered on the MCP server is wrapped by the audit hook."""
    from coach_mcp.server import mcp

    tools = mcp._tool_manager.list_tools()
    assert tools, "expected registered tools on the MCP server"
    unaudited = [tool.name for tool in tools if not getattr(tool.fn, "__audit_wrapped__", False)]
    assert unaudited == []


# ---------------------------------------------------------------------------
# Athlete ID extraction from real server models
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_athlete_id_extracted_from_real_server_model(audit_records):
    """The athlete id is read from the tool's real input model."""

    @audit_tool_call
    async def _profile_tool(params: GetAthleteProfileInput, ctx: MagicMock) -> str:
        return "ok"

    await _profile_tool(GetAthleteProfileInput(athlete_id="i12345"), MagicMock())

    entry = _entries(audit_records)[0]
    assert entry["athlete_id"] == "i12345"
