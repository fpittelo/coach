"""Security tests for secret/PII redaction and input validation hardening."""

import json

import pytest
from pydantic import ValidationError

from coach_mcp.client import IntervalsAPIError, IntervalsAuthError
from coach_mcp.models import (
    CreateActivityInput,
    CreateEventInput,
    DeleteEventInput,
    GetActivityInput,
    GetActivityStreamsInput,
    GetAthleteProfileInput,
    GetEventInput,
    GetPowerCurveInput,
    GetSportSettingsInput,
    ListActivitiesInput,
    ListFoldersInput,
    UpdateEventInput,
)
from coach_mcp.security import redact_sensitive, redact_structure
from coach_mcp.server import (
    intervals_get_athlete_profile,
)

# ---------------------------------------------------------------------------
# redact_sensitive regex tests
# ---------------------------------------------------------------------------


def test_redact_sensitive_none_and_empty():
    """redact_sensitive handles None and empty string cleanly."""
    assert redact_sensitive(None) is None
    assert redact_sensitive("") == ""


def test_redact_basic_auth():
    """Basic auth credentials are redacted."""
    text = "Authorization: Basic dXNlcjpwYXNzd29yZA=="
    assert redact_sensitive(text) == "Authorization: Basic [REDACTED]"

    text_lower = "authorization: basic abc123=="
    assert redact_sensitive(text_lower) == "authorization: Basic [REDACTED]"


def test_redact_bearer_token():
    """Bearer tokens are redacted."""
    text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token"
    assert redact_sensitive(text) == "Authorization: Bearer [REDACTED]"

    text_lower = "authorization: bearer abc.def-ghi"
    assert redact_sensitive(text_lower) == "authorization: Bearer [REDACTED]"


def test_redact_api_key_query_param():
    """API keys in query parameters are redacted while preserving key name."""
    assert redact_sensitive("url?api_key=secret123") == "url?api_key=[REDACTED]"
    assert redact_sensitive("url?apikey=secret123") == "url?apikey=[REDACTED]"
    assert redact_sensitive("url?key=secret123") == "url?key=[REDACTED]"
    assert redact_sensitive("url?API_KEY=secret123") == "url?API_KEY=[REDACTED]"
    result = redact_sensitive("url?api_key=secret123&other=value")
    assert result == "url?api_key=[REDACTED]&other=value"


def test_redact_api_key_header_prefix():
    """APIKEY header prefix values are redacted."""
    assert redact_sensitive("APIKEY secret123") == "APIKEY [REDACTED]"
    assert redact_sensitive("apikey secret123") == "APIKEY [REDACTED]"


def test_redact_api_key_colon_pattern():
    """General api_key/apikey/key colon patterns are redacted."""
    assert redact_sensitive("api_key: secret123") == "[REDACTED]"
    assert redact_sensitive("apikey: secret123") == "[REDACTED]"
    assert redact_sensitive("key: secret123") == "[REDACTED]"
    assert redact_sensitive("API_KEY: secret123") == "[REDACTED]"


def test_redact_email():
    """Email addresses are redacted."""
    assert redact_sensitive("Contact john.doe@example.com") == "Contact [REDACTED:EMAIL]"
    assert redact_sensitive("user+tag@sub.domain.co.uk") == "[REDACTED:EMAIL]"


def test_redact_sensitive_multiple_secrets():
    """Multiple secrets in one string are all redacted."""
    text = (
        "Request to https://api.example.com?api_key=secret123 "
        "with Authorization: Bearer token.abc and email user@example.com"
    )
    result = redact_sensitive(text)
    assert result is not None
    assert "secret123" not in result
    assert "token.abc" not in result
    assert "user@example.com" not in result
    assert "api_key=[REDACTED]" in result
    assert "Bearer [REDACTED]" in result
    assert "[REDACTED:EMAIL]" in result


# ---------------------------------------------------------------------------
# IntervalsAPIError redaction tests
# ---------------------------------------------------------------------------


def test_intervals_api_error_str_redacts_message():
    """IntervalsAPIError.__str__ redacts sensitive information in message."""
    err = IntervalsAPIError(
        "Failed for api_key=secret123 and user@example.com",
        status_code=500,
        response_text="details",
    )
    text = str(err)
    assert "secret123" not in text
    assert "user@example.com" not in text
    assert "[REDACTED" in text


def test_intervals_api_error_str_redacts_response_text():
    """IntervalsAPIError.__str__ redacts sensitive information in response_text."""
    err = IntervalsAPIError(
        "API error",
        status_code=400,
        response_text="Bearer leaked_token and email leak@example.com",
    )
    text = str(err)
    assert "leaked_token" not in text
    assert "leak@example.com" not in text
    assert "[REDACTED" in text


def test_intervals_auth_error_str_redacted():
    """IntervalsAuthError string representation is redacted."""
    err = IntervalsAuthError(
        "Auth failed with Basic dXNlcjpwYXNz",
        status_code=401,
        response_text="Unauthorized",
    )
    text = str(err)
    assert "dXNlcjpwYXNz" not in text
    assert "[REDACTED]" in text


# ---------------------------------------------------------------------------
# Input validation acceptance tests
# ---------------------------------------------------------------------------


def test_valid_athlete_id_patterns():
    """Athlete IDs matching '0' or 'i<digits>' are accepted."""
    assert GetAthleteProfileInput(athlete_id="0").athlete_id == "0"
    assert GetAthleteProfileInput(athlete_id="i123").athlete_id == "i123"
    assert GetAthleteProfileInput(athlete_id="i0").athlete_id == "i0"
    assert GetSportSettingsInput(athlete_id="i99999").athlete_id == "i99999"
    model = ListActivitiesInput(oldest="2026-08-01", newest="2026-08-22", athlete_id="0")
    assert model.athlete_id == "0"


def test_valid_activity_id_patterns():
    """Activity IDs with alphanumeric, underscore, and hyphen are accepted."""
    assert GetActivityInput(activity_id="i123").activity_id == "i123"
    assert GetActivityInput(activity_id="12345").activity_id == "12345"
    assert GetActivityInput(activity_id="act_123-ABC").activity_id == "act_123-ABC"


def test_valid_event_id_patterns():
    """Event IDs with alphanumeric, underscore, and hyphen are accepted."""
    assert GetEventInput(event_id="evt_123").event_id == "evt_123"
    assert GetEventInput(event_id="evt-456").event_id == "evt-456"
    model = CreateEventInput(start_date_local="2026-08-23T08:00:00", name="Test")
    assert model.start_date_local == "2026-08-23T08:00:00"


def test_valid_start_date_local_patterns():
    """start_date_local matching YYYY-MM-DDTHH:MM:SS is accepted."""
    model = CreateActivityInput(
        name="Test",
        type="Ride",
        start_date_local="2026-08-22T09:00:00",
        moving_time_seconds=3600,
    )
    assert model.start_date_local == "2026-08-22T09:00:00"

    update_model = UpdateEventInput(
        event_id="evt_123",
        start_date_local="2026-08-24T08:00:00",
    )
    assert update_model.start_date_local == "2026-08-24T08:00:00"


# ---------------------------------------------------------------------------
# Input validation rejection tests (STRIDE / injection hardening)
# ---------------------------------------------------------------------------


def test_athlete_id_rejects_path_traversal():
    """Path traversal patterns in athlete_id are rejected."""
    with pytest.raises(ValidationError):
        GetAthleteProfileInput(athlete_id="../../etc/passwd")


def test_athlete_id_rejects_command_injection():
    """Command injection patterns in athlete_id are rejected."""
    with pytest.raises(ValidationError):
        GetPowerCurveInput(athlete_id="i123; rm -rf /")


def test_athlete_id_rejects_invalid_prefix():
    """Athlete IDs not matching '0' or 'i<digits>' are rejected."""
    with pytest.raises(ValidationError):
        GetSportSettingsInput(athlete_id="abc123")

    with pytest.raises(ValidationError):
        ListFoldersInput(athlete_id="i")


def test_activity_id_rejects_path_traversal():
    """Path traversal in activity_id is rejected."""
    with pytest.raises(ValidationError):
        GetActivityInput(activity_id="../../etc/passwd")


def test_activity_id_rejects_command_injection():
    """Command injection in activity_id is rejected."""
    with pytest.raises(ValidationError):
        GetActivityStreamsInput(activity_id="i123; rm -rf /")


def test_event_id_rejects_path_traversal():
    """Path traversal in event_id is rejected."""
    with pytest.raises(ValidationError):
        GetEventInput(event_id="../../etc/passwd")


def test_event_id_rejects_command_injection():
    """Command injection in event_id is rejected."""
    with pytest.raises(ValidationError):
        DeleteEventInput(event_id="evt_123; rm -rf /")


def test_start_date_local_rejects_malformed_datetime():
    """Malformed start_date_local values are rejected."""
    with pytest.raises(ValidationError):
        CreateActivityInput(
            name="Test",
            type="Ride",
            start_date_local="2026/08/22 09:00:00",
            moving_time_seconds=3600,
        )

    with pytest.raises(ValidationError):
        CreateEventInput(
            start_date_local="2026-08-23T8:00:00",
            name="Test",
        )

    with pytest.raises(ValidationError):
        UpdateEventInput(
            event_id="evt_123",
            start_date_local="08-24-2026T08:00:00",
        )


def test_start_date_local_rejects_path_traversal():
    """Path traversal in start_date_local is rejected."""
    with pytest.raises(ValidationError):
        CreateActivityInput(
            name="Test",
            type="Ride",
            start_date_local="../../etc/passwd",
            moving_time_seconds=3600,
        )


# ---------------------------------------------------------------------------
# Swiss nLPD / PII compliance tests
# ---------------------------------------------------------------------------


def test_email_pii_redacted():
    """Email PII is redacted from arbitrary text."""
    text = "Athlete email: jane.doe@example.com"
    assert redact_sensitive(text) == "Athlete email: [REDACTED:EMAIL]"


def test_no_false_positives_on_safe_text():
    """Safe text without secrets is returned unchanged."""
    text = "Activity i123 completed on 2026-08-22 with 250W average."
    assert redact_sensitive(text) == text


# ---------------------------------------------------------------------------
# redact_structure — structured redaction for the audit path (#64)
# ---------------------------------------------------------------------------


def test_redact_structure_redacts_sensitive_keys():
    """Values stored under secret-bearing keys are replaced wholesale."""
    payload = {
        "api_key": "sk-fake-123",
        "token": "tok-fake-456",
        "Authorization": "Bearer zzz",
        "password": "hunter2",
        "keep": "visible",
    }
    result = redact_structure(payload)
    assert result["api_key"] == "[REDACTED]"
    assert result["token"] == "[REDACTED]"
    assert result["Authorization"] == "[REDACTED]"
    assert result["password"] == "[REDACTED]"
    assert result["keep"] == "visible"


def test_redact_structure_recurses_into_nested_structures():
    """Nested dicts and lists are redacted recursively."""
    payload = {
        "records": [
            {"comments": "mail me at dev@example.com", "note": "safe"},
            {"api_key": "sk-nested", "deep": {"access_token": "tok-deep"}},
        ],
    }
    result = redact_structure(payload)
    assert result["records"][0]["comments"] == "mail me at [REDACTED:EMAIL]"
    assert result["records"][0]["note"] == "safe"
    assert result["records"][1]["api_key"] == "[REDACTED]"
    assert result["records"][1]["deep"]["access_token"] == "[REDACTED]"


def test_redact_structure_preserves_non_string_scalars():
    """Non-string scalars (int, float, bool, None) pass through unchanged."""
    payload = {"count": 3, "ratio": 0.5, "flag": True, "empty": None}
    assert redact_structure(payload) == payload


def test_redact_structure_handles_plain_string_and_list():
    """Top-level strings and lists are redacted via redact_sensitive."""
    assert redact_structure("api_key=secret123") == "api_key=[REDACTED]"
    assert redact_structure(["a@b.com", 42]) == ["[REDACTED:EMAIL]", 42]


def test_redact_structure_json_serialized_sensitive_key():
    """A JSON-style payload with a sensitive key is redacted (audit leak vector)."""
    payload = {"api_key": "sk-fake-json"}
    serialized = json.dumps(payload)
    # The legacy string redaction alone cannot catch JSON-style keys...
    assert "sk-fake-json" in (redact_sensitive(serialized) or "")
    # ...but the structured redaction does.
    result = redact_structure(payload)
    assert "sk-fake-json" not in json.dumps(result)
    assert result["api_key"] == "[REDACTED]"


# ---------------------------------------------------------------------------
# redact_structure — JSON-in-string redaction (PR #88 review finding 1)
# ---------------------------------------------------------------------------


def test_redact_structure_redacts_json_in_string_value():
    """A string value containing embedded JSON has its secrets redacted.

    Reviewer repro: the #18 string redaction's colon regex requires
    ``api_key:`` without an intervening quote, so the quoted JSON form
    ``{"api_key": "..."}`` inside a string value used to survive.
    """
    payload = {"notes": '{"api_key": "sk-live-abc"}'}
    result = redact_structure(payload)
    assert "sk-live-abc" not in json.dumps(result)
    assert result["notes"] == '{"api_key": "[REDACTED]"}'


def test_redact_structure_redacts_json_in_string_inside_list():
    """JSON-in-string elements inside a list are redacted recursively."""
    payload = ["plain text", '{"token": "tok-nested-1"}']
    result = redact_structure(payload)
    assert "tok-nested-1" not in json.dumps(result)
    assert result[0] == "plain text"
    assert result[1] == '{"token": "[REDACTED]"}'


def test_redact_structure_redacts_json_array_string():
    """A string value holding a JSON array is parsed and redacted."""
    payload = {"blob": '[{"api_key": "sk-arr-1"}, {"name": "safe"}]'}
    result = redact_structure(payload)
    assert "sk-arr-1" not in json.dumps(result)
    assert result["blob"] == '[{"api_key": "[REDACTED]"}, {"name": "safe"}]'


def test_redact_structure_malformed_json_string_passes_through_as_prose():
    """A malformed JSON string is not mangled — it takes the prose path."""
    original = '{"api_key": broken json here'
    payload = {"notes": original}
    result = redact_structure(payload)
    assert result["notes"] == original


def test_redact_structure_redacts_nested_json_in_string_within_json():
    """JSON containing a nested JSON-in-string value is redacted recursively."""
    payload = {"outer": '{"inner": {"api_key": "sk-deep-1"}}'}
    result = redact_structure(payload)
    assert "sk-deep-1" not in json.dumps(result)
    assert result["outer"] == '{"inner": {"api_key": "[REDACTED]"}}'


def test_redact_structure_top_level_json_string_redacted():
    """A top-level JSON string gets the same JSON-in-string treatment."""
    result = redact_structure('{"api_key": "sk-top-1"}')
    assert "sk-top-1" not in result
    assert result == '{"api_key": "[REDACTED]"}'


# ---------------------------------------------------------------------------
# redact_structure — generic *_key / bare key names (PR #88 review finding 2)
# ---------------------------------------------------------------------------


def test_redact_structure_redacts_generic_key_suffix_names():
    """Generic *_key and bare key names are redacted, including at nested depth."""
    payload = {
        "private_key": "pk-fake-1",
        "access_key": "ak-fake-1",
        "client_key": "ck-fake-1",
        "key": "bare-fake-1",
        "nested": {"ssh_key": "sk-fake-1", "keep": "visible"},
    }
    result = redact_structure(payload)
    assert result["private_key"] == "[REDACTED]"
    assert result["access_key"] == "[REDACTED]"
    assert result["client_key"] == "[REDACTED]"
    assert result["key"] == "[REDACTED]"
    assert result["nested"]["ssh_key"] == "[REDACTED]"
    assert result["nested"]["keep"] == "visible"


def test_sensitive_key_pattern_does_not_match_embedded_words():
    """Bare 'key' matching must not swallow ordinary words containing 'key'."""
    payload = {"monkey": "see", "keyboard": "type", "hotkey": "press"}
    result = redact_structure(payload)
    assert result == payload


# ---------------------------------------------------------------------------
# Server error redaction tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_server_handler_redacts_error_message():
    """MCP tool handlers redact sensitive data in error strings."""
    from unittest.mock import AsyncMock, MagicMock

    ctx = MagicMock()
    ctx.request_context.lifespan_state = {}

    client = AsyncMock()
    client.get_athlete_profile = AsyncMock(
        side_effect=IntervalsAPIError(
            "Failed with api_key=secret123 and email leak@example.com",
            status_code=500,
        )
    )
    ctx.request_context.lifespan_state["client"] = client

    params = GetAthleteProfileInput()
    result = await intervals_get_athlete_profile(params, ctx)

    assert "Error fetching athlete profile" in result
    assert "secret123" not in result
    assert "leak@example.com" not in result
    assert "[REDACTED" in result
